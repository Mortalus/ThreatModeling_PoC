from flask import jsonify, request, send_file
from datetime import datetime
import json
import tempfile
from services.review_service import ReviewService
from models.pipeline_state import PipelineState
from utils.logging_utils import logger

def register_review_routes(app, pipeline_state: PipelineState, socketio, output_folder):
    @app.route('/api/review-queue/<int:step>', methods=['GET'])
    def get_review_queue(step):
        try:
            with pipeline_state.lock:
                step_data = pipeline_state.state.get('step_outputs', {}).get(step)
                if not step_data:
                    return jsonify({'error': 'Step not completed yet'}), 404
                if step not in pipeline_state.state['review_queue']:
                    review_items = ReviewService.generate_review_items(step, step_data)
                    pipeline_state.state['review_queue'][step] = review_items
                else:
                    review_items = pipeline_state.state['review_queue'][step]
                pending_items = [item for item in review_items if item['status'] == 'pending']
                return jsonify({
                    'step': step,
                    'items': pending_items,
                    'total': len(review_items),
                    'pending': len(pending_items)
                })
        except Exception as e:
            logger.error(f"Review queue error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/review-item/<item_id>', methods=['POST'])
    def review_item(item_id):
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            with pipeline_state.lock:
                for step, items in pipeline_state.state.get('review_queue', {}).items():
                    for item in items:
                        if item['id'] == item_id:
                            item['status'] = 'reviewed'
                            item['review'] = {
                                'reviewer': data.get('reviewer', 'Unknown'),
                                'timestamp': datetime.now().isoformat(),
                                'decision': data.get('decision'),
                                'corrections': data.get('corrections', {}),
                                'comments': data.get('comments')
                            }
                            if data.get('decision') == 'approve' and data.get('corrections'):
                                ReviewService.apply_review_corrections(step, item, data.get('corrections', {}), pipeline_state, output_folder)
                            pipeline_state.state['review_history'].append({
                                'item_id': item_id,
                                'step': step,
                                'timestamp': datetime.now().isoformat(),
                                **item['review']
                            })
                            pipeline_state.add_log(f"Review submitted for {item['type']} by {data.get('reviewer')}", 'info')
                            socketio.emit('review_update', {
                                'item_id': item_id,
                                'status': 'reviewed',
                                'reviewer': data.get('reviewer')
                            })
                            return jsonify({
                                'status': 'success',
                                'item_id': item_id,
                                'remaining': pipeline_state.count_pending_reviews()
                            })
            return jsonify({'error': 'Item not found'}), 404
        except Exception as e:
            logger.error(f"Review submission error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/review-summary', methods=['GET'])
    def get_review_summary():
        try:
            summary = {
                'total_items': 0,
                'reviewed': 0,
                'pending': 0,
                'by_step': {},
                'by_type': {},
                'recent_reviews': [],
                'quality_metrics': ReviewService.calculate_quality_metrics(pipeline_state.state.get('review_history', []))
            }
            with pipeline_state.lock:
                for step, items in pipeline_state.state.get('review_queue', {}).items():
                    step_summary = {
                        'total': len(items),
                        'reviewed': len([i for i in items if i['status'] == 'reviewed']),
                        'pending': len([i for i in items if i['status'] == 'pending'])
                    }
                    summary['by_step'][step] = step_summary
                    summary['total_items'] += step_summary['total']
                    summary['reviewed'] += step_summary['reviewed']
                    summary['pending'] += step_summary['pending']
                    for item in items:
                        item_type = item['type']
                        if item_type not in summary['by_type']:
                            summary['by_type'][item_type] = {'total': 0, 'reviewed': 0}
                        summary['by_type'][item_type]['total'] += 1
                        if item['status'] == 'reviewed':
                            summary['by_type'][item_type]['reviewed'] += 1
                summary['recent_reviews'] = sorted(
                    pipeline_state.state.get('review_history', []),
                    key=lambda x: x['timestamp'],
                    reverse=True
                )[:10]
            return jsonify(summary)
        except Exception as e:
            logger.error(f"Review summary error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/batch-review', methods=['POST'])
    def batch_review():
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            item_ids = data.get('item_ids', [])
            reviewer = data.get('reviewer', 'Unknown')
            decision = data.get('decision', 'approve')
            reviewed_count = 0
            with pipeline_state.lock:
                for step, items in pipeline_state.state.get('review_queue', {}).items():
                    for item in items:
                        if item['id'] in item_ids and item['status'] == 'pending':
                            item['status'] = 'reviewed'
                            item['review'] = {
                                'reviewer': reviewer,
                                'timestamp': datetime.now().isoformat(),
                                'decision': decision,
                                'batch': True,
                                'comments': f"Batch {decision}"
                            }
                            pipeline_state.state['review_history'].append({
                                'item_id': item['id'],
                                'step': step,
                                'timestamp': datetime.now().isoformat(),
                                **item['review']
                            })
                            reviewed_count += 1
            pipeline_state.add_log(f"Batch review: {reviewed_count} items {decision}ed by {reviewer}", 'info')
            socketio.emit('batch_review_complete', {
                'count': reviewed_count,
                'decision': decision,
                'reviewer': reviewer
            })
            return jsonify({
                'status': 'success',
                'reviewed_count': reviewed_count,
                'remaining': pipeline_state.count_pending_reviews()
            })
        except Exception as e:
            logger.error(f"Batch review error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/export/review-report', methods=['GET'])
    def export_review_report():
        try:
            with pipeline_state.lock:
                report = {
                    'generated_at': datetime.now().isoformat(),
                    'session_id': pipeline_state.state['current_session'],
                    'review_summary': {
                        'total_items_reviewed': len(pipeline_state.state['review_history']),
                        'reviewers': list(set(r['reviewer'] for r in pipeline_state.state['review_history'])),
                        'pending_reviews': pipeline_state.count_pending_reviews()
                    },
                    'quality_metrics': ReviewService.calculate_quality_metrics(pipeline_state.state['review_history']),
                    'review_details': pipeline_state.state['review_history']
                }
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(report, temp_file, indent=2)
            temp_file.close()
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f'review_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                mimetype='application/json'
            )
        except Exception as e:
            logger.error(f"Review report error: {e}")
            return jsonify({'error': str(e)}), 500