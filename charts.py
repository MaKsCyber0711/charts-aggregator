#!/usr/bin/env python3
"""
Charts Aggregator - holt aktuelle Charts von FM4, Beatport und anderen Quellen
und verlinkt die Songs direkt zu Apple Music.
"""

import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
from datetime import datetime


def get_fm4_charts():
    """Holt die aktuellen FM4 Charts von der ORF/FM4 Website."""
    print("  Lade FM4 Charts...")
    tracks = []
    try:
        url = "https://fm4.orf.at/charts"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")

        # FM4 Charts werden als Liste dargestellt
        items = soup.select(".chart-item, .charts-item, li.item")
        for i, item in enumerate(items[:20], 1):
            artist_el = item.select_one(".artist, .chart-artist")
            title_el = item.select_one(".title, .chart-title, h3, h4")
            if artist_el and title_el:
                tracks.append({
                    "rank": i,
                    "artist": artist_el.get_text(strip=True),
                    "title": title_el.get_text(strip=True),
                })
    except Exception as e:
        print(f"  FM4 Fehler: {e}")

    if not tracks:
        # Fallback: Demo-Daten wenn Scraping fehlschlägt
        tracks = [
            {"rank": 1, "artist": "Billie Eilish", "title": "BIRDS OF A FEATHER"},
            {"rank": 2, "artist": "Sabrina Carpenter", "title": "Espresso"},
            {"rank": 3, "artist": "Chappell Roan", "title": "Good Luck, Babe!"},
            {"rank": 4, "artist": "Charli XCX", "title": "360"},
            {"rank": 5, "artist": "Vampire Weekend", "title": "Mary Boone"},
        ]
        print("  (Demo-Daten verwendet)")
    return tracks


def get_beatport_charts():
    """Holt die aktuellen Beatport Top 10 Charts."""
    print("  Lade Beatport Charts...")
    tracks = []
    try:
        url = "https://www.beatport.com/top-100"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")

        items = soup.select(".track-title, [class*='TrackName'], [data-testid*='track']")
        for i, item in enumerate(items[:20], 1):
            text = item.get_text(strip=True)
            if text:
                tracks.append({"rank": i, "artist": "—", "title": text})
    except Exception as e:
        print(f"  Beatport Fehler: {e}")

    if not tracks:
        # Fallback: Demo-Daten
        tracks = [
            {"rank": 1, "artist": "Fisher & Aaaron Roan", "title": "Atmosphere"},
            {"rank": 2, "artist": "Chris Avantgarde", "title": "Siren"},
            {"rank": 3, "artist": "Anyma", "title": "Welcome To The Opera"},
            {"rank": 4, "artist": "Innellea", "title": "Vertigo"},
            {"rank": 5, "artist": "Tale Of Us", "title": "Pleiades"},
        ]
        print("  (Demo-Daten verwendet)")
    return tracks


def get_apple_music_link(artist, title):
    """Erstellt einen Apple Music Suchlink für einen Song."""
    query = f"{artist} {title}"
    encoded = urllib.parse.quote(query)
    return f"https://music.apple.com/search?term={encoded}"


def build_html(fm4_charts, beatport_charts):
    """Erstellt eine schöne HTML-Seite mit allen Charts."""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    def chart_rows(tracks):
        rows = ""
        for t in tracks:
            link = get_apple_music_link(t["artist"], t["title"])
            rows += f"""
        <tr>
          <td class="rank">#{t['rank']}</td>
          <td class="artist">{t['artist']}</td>
          <td class="title">{t['title']}</td>
          <td><a href="{link}" target="_blank" class="apple-btn">🎵 Apple Music</a></td>
        </tr>"""
        return rows

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Charts Aggregator</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f0f0f;
      color: #f0f0f0;
      padding: 2rem;
    }}
    h1 {{
      font-size: 2rem;
      margin-bottom: 0.25rem;
      background: linear-gradient(90deg, #ff6b6b, #a855f7);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .updated {{ color: #666; font-size: 0.85rem; margin-bottom: 2.5rem; }}
    .charts-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
      gap: 2rem;
    }}
    .chart-section h2 {{
      font-size: 1.2rem;
      margin-bottom: 1rem;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid #333;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    tr:hover {{ background: #1a1a1a; }}
    td {{ padding: 0.6rem 0.5rem; border-bottom: 1px solid #222; font-size: 0.9rem; }}
    .rank {{ color: #666; width: 40px; }}
    .artist {{ color: #a0a0a0; width: 35%; }}
    .title {{ font-weight: 500; }}
    .apple-btn {{
      display: inline-block;
      background: #fc3c44;
      color: white;
      text-decoration: none;
      padding: 0.25rem 0.75rem;
      border-radius: 20px;
      font-size: 0.8rem;
      white-space: nowrap;
    }}
    .apple-btn:hover {{ background: #e0353d; }}
  </style>
</head>
<body>
  <h1>Charts Aggregator</h1>
  <p class="updated">Zuletzt aktualisiert: {now}</p>

  <div class="charts-grid">
    <div class="chart-section">
      <h2>📻 FM4 Charts</h2>
      <table>
        <tbody>{chart_rows(fm4_charts)}</tbody>
      </table>
    </div>
    <div class="chart-section">
      <h2>🎛️ Beatport Top 100</h2>
      <table>
        <tbody>{chart_rows(beatport_charts)}</tbody>
      </table>
    </div>
  </div>
</body>
</html>"""
    return html


def main():
    print("=== Charts Aggregator ===")
    print()
    print("Lade Charts...")

    fm4 = get_fm4_charts()
    beatport = get_beatport_charts()

    print()
    print("Erstelle charts.html ...")
    html = build_html(fm4, beatport)

    with open("charts.html", "w", encoding="utf-8") as f:
        f.write(html)

    print()
    print("✅ Fertig! Öffne 'charts.html' in deinem Browser.")
    print()
    print("FM4 Top 5:")
    for t in fm4[:5]:
        print(f"  #{t['rank']} {t['artist']} – {t['title']}")
    print()
    print("Beatport Top 5:")
    for t in beatport[:5]:
        print(f"  #{t['rank']} {t['artist']} – {t['title']}")


if __name__ == "__main__":
    main()
