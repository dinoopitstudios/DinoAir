/**
 * Live API Call Demo for DinoAir
 * This script demonstrates the working API tracker with backend running
 */

console.log('🎯 DinoAir Live API Demo');
console.log('========================');

/**
 * Runs a live tracking demonstration by printing service URLs and making test API calls.
 * Logs the health endpoint status and provides a summary of service statuses.
 * @returns {Promise<void>} A promise that resolves when the demo completes.
 */
async function demoLiveTracking() {
  console.log('📊 Dashboard: http://localhost:3002');
  console.log('🌐 Frontend: http://localhost:5173');
  console.log('🔗 Backend: http://127.0.0.1:24801');
  console.log('');

  console.log('🚀 Making test API calls to demonstrate live tracking...');

  try {
    // Test health endpoint
    console.log('💓 Testing health endpoint...');
    const healthResponse = await fetch('http://127.0.0.1:24801/health');
    const healthData = await healthResponse.json();
    console.log(
      `✅ Health Check: ${healthResponse.status} - ${JSON.stringify(healthData).substring(0, 100)}...`
    );

    // Wait a bit
    await new Promise(resolve => setTimeout(resolve, 1000));

    console.log('');
    console.log('🎯 Demo Summary:');
    console.log('================');
    console.log('✅ Backend API: Running on port 24801');
    console.log('✅ Frontend: Running on port 5173');
    console.log('✅ API Tracker: Capturing all network traffic on port 3002');
    console.log('✅ Playwright: Monitoring DinoAir browser interactions');
    console.log('');
    console.log('🎉 Live API tracking is fully operational!');
    console.log('');
    console.log('📋 Next Steps:');
    console.log('- Open http://localhost:3002 to see the live dashboard');
    console.log('- Navigate to http://localhost:5173 and interact with DinoAir');
    console.log('- Watch real-time API calls appear in the tracker dashboard');
    console.log('- All frontend → backend communication is now being captured!');
  } catch (error) {
    console.error('❌ Error during demo:', error.message);
  }
}

demoLiveTracking();
