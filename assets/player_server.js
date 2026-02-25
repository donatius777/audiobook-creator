/**
 * Audiobook streaming server with web player.
 * Serves chapter audio files and provides a download-all endpoint.
 *
 * Usage: AUDIO_DIR=<path> TITLE=<title> AUTHOR=<author> CHAPTERS_JSON=<json> node player_server.js
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.env.PORT || '8080');
const AUDIO_DIR = process.env.AUDIO_DIR || './audio';
const TITLE = process.env.TITLE || 'Audiobook';
const AUTHOR = process.env.AUTHOR || 'Unknown';
const HTML_FILE = process.env.HTML_FILE || path.join(__dirname, 'player.html');

let chapters;
try {
  chapters = JSON.parse(process.env.CHAPTERS_JSON || '[]');
} catch(e) {
  // Try loading from file
  const chapFile = path.join(AUDIO_DIR, 'chapters.json');
  if (fs.existsSync(chapFile)) {
    chapters = JSON.parse(fs.readFileSync(chapFile, 'utf-8'));
  } else {
    // Auto-discover MP3 files
    chapters = fs.readdirSync(AUDIO_DIR)
      .filter(function(f) { return f.endsWith('.mp3'); })
      .sort()
      .map(function(f, i) {
        return { file: f, title: 'Chapter ' + (i + 1) };
      });
  }
}

const server = http.createServer(function(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Range');
  res.setHeader('Access-Control-Expose-Headers', 'Content-Range, Content-Length, Accept-Ranges');

  if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

  var url = req.url.split('?')[0];

  if (url === '/' || url === '/index.html') {
    if (fs.existsSync(HTML_FILE)) {
      var html = fs.readFileSync(HTML_FILE, 'utf-8');
      // Inject title/author
      html = html.replace('{{TITLE}}', TITLE).replace('{{AUTHOR}}', AUTHOR);
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
    } else {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><body><h1>' + TITLE + '</h1><p>Player HTML not found.</p></body></html>');
    }
    return;
  }

  if (url === '/api/chapters') {
    var data = chapters.map(function(c, i) {
      return { id: i, title: c.title, url: '/audio/' + c.file };
    });
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(data));
    return;
  }

  if (url === '/download-all') {
    var totalSize = 0;
    var validFiles = [];
    for (var di = 0; di < chapters.length; di++) {
      var fp = path.join(AUDIO_DIR, chapters[di].file);
      if (fs.existsSync(fp)) {
        totalSize += fs.statSync(fp).size;
        validFiles.push(fp);
      }
    }
    var safeName = TITLE.replace(/[^a-zA-Z0-9 _-]/g, '').replace(/\s+/g, '_');
    res.writeHead(200, {
      'Content-Type': 'application/octet-stream',
      'Content-Length': totalSize,
      'Content-Disposition': 'attachment; filename="' + safeName + '_Audiobook.mp3"',
    });
    var fileIdx = 0;
    function streamNext() {
      if (fileIdx >= validFiles.length) { res.end(); return; }
      var rs = fs.createReadStream(validFiles[fileIdx]);
      fileIdx++;
      rs.pipe(res, { end: false });
      rs.on('end', streamNext);
      rs.on('error', function() { streamNext(); });
    }
    streamNext();
    return;
  }

  if (url.indexOf('/audio/') === 0) {
    var filename = path.basename(url);
    var filepath = path.join(AUDIO_DIR, filename);
    if (!fs.existsSync(filepath)) { res.writeHead(404); res.end('Not found'); return; }

    var stat = fs.statSync(filepath);
    var fileSize = stat.size;
    var range = req.headers.range;

    if (range) {
      var parts = range.replace(/bytes=/, '').split('-');
      var start = parseInt(parts[0], 10);
      var end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
      var chunksize = end - start + 1;
      res.writeHead(206, {
        'Content-Range': 'bytes ' + start + '-' + end + '/' + fileSize,
        'Accept-Ranges': 'bytes',
        'Content-Length': chunksize,
        'Content-Type': 'audio/mpeg',
      });
      fs.createReadStream(filepath, { start: start, end: end }).pipe(res);
    } else {
      res.writeHead(200, {
        'Content-Length': fileSize,
        'Content-Type': 'audio/mpeg',
        'Accept-Ranges': 'bytes',
      });
      fs.createReadStream(filepath).pipe(res);
    }
    return;
  }

  res.writeHead(404);
  res.end('Not found');
});

server.listen(PORT, '0.0.0.0', function() {
  console.log('Audiobook server running on port ' + PORT);
  console.log('Title: ' + TITLE + ' | Author: ' + AUTHOR);
  console.log('Chapters: ' + chapters.length + ' | Audio dir: ' + AUDIO_DIR);
});
