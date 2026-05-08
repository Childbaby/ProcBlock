import { createServer } from 'https';
import { parse } from 'url';
import next from 'next';
import { readFileSync } from 'fs';

const PORT = 3000;
const app = next({ dev: true, hostname: '0.0.0.0', port: PORT });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  createServer(
    {
      key: readFileSync('./localhost+2-key.pem'),
      cert: readFileSync('./localhost+2.pem'),
    },
    (req, res) => {
      const parsedUrl = parse(req.url, true);
      handle(req, res, parsedUrl);
    }
  ).listen(PORT, '0.0.0.0', (err) => {
    if (err) throw err;
    console.log(`> Ready on https://0.0.0.0:${PORT}`);
  });
});
