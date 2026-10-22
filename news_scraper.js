const Parser = require('rss-parser');
const parser = new Parser({
  headers: {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
  }
});

const RSS_SOURCES = [
  { name: 'Fotomaç', url: 'https://www.fotomac.com.tr/rss/anasayfa.xml' },
  { name: 'A Spor', url: 'https://www.aspor.com.tr/rss/anasayfa.xml' },
  { name: 'NTV Spor Skor', url: 'https://www.ntv.com.tr/sporskor.rss' },
  { name: 'Fanatik Süper Lig', url: 'https://www.fanatik.com.tr/rss/super-lig' }
];

async function getLatestFootballNews() {
  const allNews = [];

  for (const source of RSS_SOURCES) {
    try {
      const feed = await parser.parseURL(source.url);
      if (feed && feed.items) {
        feed.items.slice(0, 6).forEach(item => {
          allNews.push({
            source: source.name,
            title: item.title,
            link: item.link,
            content: item.contentSnippet || item.content || ''
          });
        });
      }
    } catch (e) {
      // sessizce diğerine geç
    }
  }

  // Fenerbahçe, Galatasaray, Beşiktaş, Trabzonspor, Transfer odaklı filtreleme
  const prioritized = allNews.filter(n => {
    const text = (n.title + ' ' + n.content).toLowerCase();
    return text.includes('fenerbahçe') || text.includes('galatasaray') || text.includes('beşiktaş') || text.includes('trabzonspor') || text.includes('transfer') || text.includes('süper lig');
  });

  return prioritized.length > 0 ? prioritized : allNews;
}

module.exports = { getLatestFootballNews };
