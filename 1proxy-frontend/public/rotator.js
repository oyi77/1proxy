const net = require('net');
const http = require('http');

const API_BASE = "http://localhost:8000";

// --- Simple Argument Parser (Dependency Free) ---
function parseArgs() {
    const args = {};
    for (let i = 2; i < process.argv.length; i++) {
        const arg = process.argv[i];
        if (arg.startsWith('--')) {
            const key = arg.slice(2);
            const value = process.argv[i + 1];
            if (value && !value.startsWith('--')) {
                args[key] = value;
                i++;
            } else {
                args[key] = true;
            }
        }
    }
    return args;
}
// ------------------------------------------------

async function getProxy(apiUrl, filters) {
    const params = new URLSearchParams();
    if (filters.protocol) params.append('protocol', filters.protocol);
    if (filters.country) params.append('country_code', filters.country);
    if (filters.anonymity) params.append('anonymity', filters.anonymity);
    if (filters.quality) params.append('min_quality', filters.quality);
    if (filters.maxLatency) params.append('max_latency', filters.maxLatency);

    const url = `${apiUrl}/api/v1/proxies/random${params.toString() ? '?' + params.toString() : ''}`;

    return new Promise((resolve) => {
        const req = http.get(url, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                if (res.statusCode === 200) {
                    try {
                        const json = JSON.parse(data);
                        resolve(json);
                    } catch (e) {
                        resolve(null);
                    }
                } else {
                    resolve(null);
                }
            });
        });

        req.on('error', (err) => {
            // Silently fail on connection errors to keep rotator alive
            resolve(null);
        });
    });
}

function startServer(port, filters, apiUrl) {
    const server = net.createServer((clientSocket) => {
        clientSocket.pause();

        getProxy(apiUrl, filters).then((proxyInfo) => {
            if (!proxyInfo) {
                clientSocket.destroy();
                return;
            }

            const remoteSocket = net.connect(proxyInfo.port, proxyInfo.ip, () => {
                console.log(`Tunneling via ${proxyInfo.protocol}://${proxyInfo.ip}:${proxyInfo.port}`);
                clientSocket.pipe(remoteSocket);
                remoteSocket.pipe(clientSocket);
                clientSocket.resume();
            });

            remoteSocket.on('error', (err) => {
                clientSocket.destroy();
            });

            clientSocket.on('error', (err) => {
                remoteSocket.destroy();
            });

            // Timeout handling
            remoteSocket.setTimeout(10000);
            remoteSocket.on('timeout', () => {
                remoteSocket.destroy();
                clientSocket.destroy();
            });
        });
    });

    server.on('error', (err) => {
        console.error(`Server error: ${err.message}`);
    });

    server.listen(port, '0.0.0.0', () => {
        console.log(`\x1b[35m%s\x1b[0m`, `
   __                                
  /  |                               
 _$$ |_    ______    ______   __    __ 
/ $$   |  /      \\  /      \\ /  |  /  |
$$$$$$/  /$$$$$$  |/$$$$$$  |$$ |  $$ |
  $$ | __$$ |  $$/ $$ |  $$ |$$ |  $$ |
  $$ |/  |$$ |     $$ \\__$$ |$$ \\__$$ |
  $$  $$/ $$ |     $$    $$/ $$    $$ |
   $$$$/  $$/       $$$$$$/   $$$$$$$ |
                             /  \\__$$ |
                             $$    $$/ 
                              $$$$$$/  
        `);
        console.log(`✅ Local Rotator running on port ${port}`);
        console.log(`📡 API: ${apiUrl}`);
        console.log(`🎯 Filters: ${JSON.stringify(filters)}`);
        console.log(`📝 Usage: node rotator.js --port 8080 --country US --protocol http`);
    });
}

const args = parseArgs();
const filters = {
    protocol: args.protocol,
    country: args.country,
    anonymity: args.anonymity,
    quality: args.quality,
    maxLatency: args['max-latency']
};

startServer(args.port || 8080, filters, args.api || API_BASE);
