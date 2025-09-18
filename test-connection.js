#!/usr/bin/env node

import http from 'http';

async function testConnection(url, name) {
    return new Promise((resolve) => {
        const urlObj = new URL(url);
        const options = {
            hostname: urlObj.hostname,
            port: urlObj.port,
            path: urlObj.pathname,
            method: 'GET',
            timeout: 5000
        };

        const req = http.request(options, (res) => {
            console.log(`✅ ${name}: Status ${res.statusCode}`);
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                console.log(`   Response: ${data.substring(0, 100)}...`);
                resolve(true);
            });
        });

        req.on('error', (error) => {
            console.log(`❌ ${name}: ${error.message}`);
            resolve(false);
        });

        req.on('timeout', () => {
            console.log(`❌ ${name}: Timeout`);
            req.destroy();
            resolve(false);
        });

        req.end();
    });
}

async function main() {
    console.log('🔍 DinoAir Connection Test');
    console.log('==========================');

    await testConnection('http://127.0.0.1:24801/health', 'API Health');
    await testConnection('http://localhost:5173/', 'Frontend');

    console.log('\nTest completed!');
}

main().catch(console.error);
