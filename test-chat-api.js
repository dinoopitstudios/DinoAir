#!/usr/bin/env node

async function testChatAPI() {
    console.log('🔍 Testing DinoAir Chat API with LM Studio');
    console.log('==========================================');

    const testMessage = {
        messages: [
            { role: 'user', content: 'Hello! Can you introduce yourself?' }
        ],
        model: 'llama-3.1-8b-instruct',
        temperature: 0.7,
        max_tokens: 100,
        extra_params: {
            router_tag: 'chat'
        }
    };

    try {
        console.log('📤 Sending chat request...');
        console.log('Request:', JSON.stringify(testMessage, null, 2));

        const response = await fetch('http://127.0.0.1:24801/ai/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(testMessage)
        });

        console.log(`📡 Response Status: ${response.status}`);

        if (!response.ok) {
            const errorText = await response.text();
            console.log(`❌ Error Response: ${errorText}`);
            return;
        }

        const result = await response.json();
        console.log('📥 Response:', JSON.stringify(result, null, 2));

        if (result.success && result.content) {
            console.log('✅ Chat API working successfully!');
            console.log(`🤖 AI Response: ${result.content}`);
        } else {
            console.log('❌ Chat API returned unsuccessful response');
        }

    } catch (error) {
        console.log(`❌ Error testing chat API: ${error.message}`);
    }
}

testChatAPI().catch(console.error);
