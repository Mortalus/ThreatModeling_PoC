#!/bin/bash

echo "🔍 Debugging Pipeline Status"
echo "============================"
echo ""

# Check output files
echo "📁 Checking output directory for DFD results..."
if [ -d "output" ]; then
    echo "Recent DFD output files:"
    ls -la output/*dfd*.json 2>/dev/null | tail -5
    
    # Find the most recent DFD file
    latest_dfd=$(ls -t output/*dfd*.json 2>/dev/null | head -1)
    if [ -n "$latest_dfd" ]; then
        echo ""
        echo "✅ Found DFD output: $latest_dfd"
        echo "File size: $(wc -c < "$latest_dfd") bytes"
        echo ""
        echo "First 500 characters:"
        echo "----------------------"
        head -c 500 "$latest_dfd"
        echo ""
        echo "----------------------"
    else
        echo "❌ No DFD output files found"
    fi
else
    echo "❌ Output directory not found"
fi

# Check log files
echo ""
echo "📋 Checking recent logs..."
if [ -d "logs" ]; then
    latest_log=$(ls -t logs/*.log 2>/dev/null | head -1)
    if [ -n "$latest_log" ]; then
        echo "Latest log: $latest_log"
        echo "Last 20 lines:"
        echo "----------------------"
        tail -20 "$latest_log"
        echo "----------------------"
    fi
fi

# Check Flask console output
echo ""
echo "💡 To see detailed Flask output:"
echo "1. Look at the Flask console where you ran 'python app.py'"
echo "2. The error details should be visible there"
echo ""
echo "Common issues and fixes:"
echo "• Timeout: The LLM call might be taking too long (increase timeout in settings)"
echo "• Memory: The document might be too large (try a smaller document)"
echo "• API limits: You might have hit rate limits (wait a minute and try again)"
echo ""
echo "To get more details, you can also:"
echo "1. Check Flask console for the full error"
echo "2. Run: tail -f output/*.log (to see live logs)"
echo "3. Check: cat output/pipeline_state.json"