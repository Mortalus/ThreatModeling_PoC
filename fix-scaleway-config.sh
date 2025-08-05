#!/bin/bash

echo "🔧 Fixing Scaleway Configuration..."
echo "==================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    touch .env
fi

echo "Current .env contents:"
echo "----------------------"
cat .env 2>/dev/null || echo "(empty)"
echo "----------------------"
echo ""

# Check if the placeholder is still there
if grep -q "your_scaleway_api_key_here" .env 2>/dev/null; then
    echo "⚠️  WARNING: You still have the placeholder API key!"
    echo ""
    echo "You need to replace it with your ACTUAL Scaleway API key."
    echo ""
    echo "To get your API key:"
    echo "1. Go to https://console.scaleway.com/"
    echo "2. Click on your organization name (top-right)"
    echo "3. Go to 'Credentials' -> 'API Keys'"
    echo "4. Create or copy an existing API key"
    echo ""
    read -p "Enter your Scaleway API key: " api_key
    
    if [ -n "$api_key" ]; then
        # Update the .env file
        sed -i.bak "s/your_scaleway_api_key_here/$api_key/" .env
        echo "✅ Updated API key in .env"
    fi
fi

# Update or add the base URL with organization ID
echo ""
echo "Updating Scaleway base URL..."

# Create a complete .env if needed
cat > .env.new << 'EOF'
# Scaleway API Configuration
SCW_SECRET_KEY=${SCW_SECRET_KEY}
SCW_API_URL=https://api.scaleway.ai/4a8fd76b-8606-46e6-afe6-617ce8eeb948/v1

# Flask Configuration
FLASK_ENV=development
PORT=5000
EOF

# Preserve existing API key if set
if [ -f ".env" ] && grep -q "SCW_SECRET_KEY=" .env; then
    existing_key=$(grep "SCW_SECRET_KEY=" .env | cut -d'=' -f2)
    sed -i.bak "s/\${SCW_SECRET_KEY}/$existing_key/" .env.new
else
    sed -i.bak "s/\${SCW_SECRET_KEY}/your_actual_api_key_here/" .env.new
fi

mv .env .env.old 2>/dev/null
mv .env.new .env

echo "✅ Updated .env file with correct base URL"
echo ""

# Update runtime config to use the correct model
if [ -f "output/runtime_config.json" ]; then
    python3 -c "
import json
with open('output/runtime_config.json', 'r') as f:
    config = json.load(f)
config['llm_model'] = 'llama-3.3-70b-instruct'
config['scw_api_url'] = 'https://api.scaleway.ai/4a8fd76b-8606-46e6-afe6-617ce8eeb948/v1'
with open('output/runtime_config.json', 'w') as f:
    json.dump(config, f, indent=2)
print('✅ Updated runtime_config.json')
"
fi

echo ""
echo "📋 Configuration Summary:"
echo "========================"
echo "• Model: llama-3.3-70b-instruct ✅"
echo "• Base URL: https://api.scaleway.ai/4a8fd76b-8606-46e6-afe6-617ce8eeb948/v1 ✅"
echo ""

# Check if API key is set
if grep -q "your_actual_api_key_here" .env 2>/dev/null; then
    echo "⚠️  IMPORTANT: You still need to add your API key!"
    echo "   Edit .env and replace 'your_actual_api_key_here' with your real key"
else
    echo "• API Key: Configured ✅"
fi

echo ""
echo "🚀 Next steps:"
echo "1. Make sure your API key is set in .env"
echo "2. Restart Flask backend: python app.py"
echo "3. The pipeline should now work!"