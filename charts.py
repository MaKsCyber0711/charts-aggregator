#!/usr/bin/env python3
"""
Charts Aggregator - holt aktuelle Charts von FM4, Apple Music und anderen Quellen
und verlinkt die Songs direkt zu Apple Music.
"""

import requests
import json
import urllib.parse
from datetime import datetime, timedelta


def get_fm4_charts():
    """Holt die gespielten Songs aus der FM4 Charts Sendung via ORF API."""
    print("  Lade FM4 Charts...")
    tracks = []
    try:
        # Suche in den letzten 7 Tagen nach der FM4 Charts Sendung (4CH)
        broadcasts_url = "https://audioapi.orf.at/fm4/api/json/current/broadcasts"
        r = requests.get(broadcasts_url, timeout=10)
        data = r.json()

        chart_href = None
        for day in data:
            for b in day.get("broadcasts", []):
                if b.get("programKey") == "4CH":
                    chart_href = b.get("href")
                    break
            if chart_href:
                break

        if not chart_href:
            raise ValueError("Keine FM4 Charts Sendung gefunden")

        # Hole die einzelnen Songs aus der Sendung
        r2 = requests.get(chart_href, timeout=10)
        detail = r2.json()
        items = detail.get("items", [])

        seen = set()
        rank = 1
        for item in items:
            if item.get("type") == "M" and item.get("interpreter") and item.get("title"):
                key = (item["interpreter"].lower(), item["title"].lower())
                if key not in seen:
                    seen.add(key)
                    tracks.append({
                        "rank": rank,
                        "artist": item["interpreter"],
                        "title": item["title"],
                    })
                    rank += 1
                    if rank > 20:
                        break

        print(f"  {len(tracks)} Songs geladen.")
    except Exception as e:
        print(f"  FM4 Fehler: {e}")

    return tracks


def get_apple_music_charts(country="at", limit=20):
    """Holt die offiziellen Apple Music Top Songs Charts."""
    print(f"  Lade Apple Music Charts ({country.upper()})...")
    tracks = []
    try:
        url = f"https://rss.applemarketingtools.com/api/v2/{country}/music/most-played/{limit}/songs.json"
        r = requests.get(url, timeout=10)
        data = r.json()
        results = data.get("feed", {}).get("results", [])
        for i, item in enumerate(results, 1):
            tracks.append({
                "rank": i,
                "artist": item.get("artistName", "—"),
                "title": item.get("name", "—"),
                "apple_music_url": item.get("url", ""),
            })
        print(f"  {len(tracks)} Songs geladen.")
    except Exception as e:
        print(f"  Apple Music Charts Fehler: {e}")

    return tracks


def get_itunes_charts(country="at", limit=20):
    """Holt iTunes/Apple Music Charts als Backup."""
    print(f"  Lade iTunes Charts ({country.upper()})...")
    tracks = []
    try:
        url = f"https://itunes.apple.com/{country}/rss/topsongs/limit={limit}/json"
        r = requests.get(url, timeout=10)
        data = r.json()
        entries = data.get("feed", {}).get("entry", [])
        for i, entry in enumerate(entries, 1):
            artist = entry.get("im:artist", {}).get("label", "—")
            title = entry.get("im:name", {}).get("label", "—")
            link = entry.get("link", {}).get("attributes", {}).get("href", "")
            tracks.append({"rank": i, "artist": artist, "title": title, "apple_music_url": link})
        print(f"  {len(tracks)} Songs geladen.")
    except Exception as e:
        print(f"  iTunes Fehler: {e}")
    return tracks


def get_apple_music_link(artist, title, existing_url=""):
    """Gibt einen Apple Music Link zurück (direkt oder Suche)."""
    if existing_url:
        return existing_url
    query = urllib.parse.quote(f"{artist} {title}")
    return f"https://music.apple.com/search?term={query}"


def build_html(sections):
    """Erstellt eine schöne HTML-Seite mit allen Charts."""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    def chart_rows(tracks):
        rows = ""
        for t in tracks:
            link = get_apple_music_link(t["artist"], t["title"], t.get("apple_music_url", ""))
            rows += f"""
        <tr>
          <td class="rank">#{t['rank']}</td>
          <td class="artist">{t['artist']}</td>
          <td class="title">{t['title']}</td>
          <td><a href="{link}" target="_blank" class="apple-btn">&#9835; Apple Music</a></td>
        </tr>"""
        return rows

    sections_html = ""
    for section in sections:
        if section["tracks"]:
            sections_html += f"""
    <div class="chart-section">
      <h2>{section['icon']} {section['name']}</h2>
      <table>
        <tbody>{chart_rows(section['tracks'])}</tbody>
      </table>
    </div>"""

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
    .no-data {{ color: #555; font-style: italic; padding: 1rem 0; }}
  </style>
</head>
<body>
  <h1>Charts Aggregator</h1>
  <p class="updated">Zuletzt aktualisiert: {now}</p>

  <div class="charts-grid">
    {sections_html}
  </div>
</body>
</html>"""
    return html


def main():
    print("=== Charts Aggregator ===")
    print()
    print("Lade Charts...")

    fm4 = get_fm4_charts()
    apple_at = get_apple_music_charts(country="at", limit=20)
    apple_de = get_apple_music_charts(country="de", limit=20)

    sections = [
        {"name": "FM4 Charts", "icon": "📻", "tracks": fm4},
        {"name": "Apple Music Österreich", "icon": "🇦🇹", "tracks": apple_at},
        {"name": "Apple Music Deutschland", "icon": "🇩🇪", "tracks": apple_de},
    ]

    print()
    print("Erstelle charts.html ...")
    html = build_html(sections)

    with open("charts.html", "w", encoding="utf-8") as f:
        f.write(html)

    print()
    print("✅ Fertig! Öffne 'charts.html' in deinem Browser.")
    print()
    for section in sections:
        if section["tracks"]:
            print(f"{section['icon']} {section['name']} Top 3:")
            for t in section["tracks"][:3]:
                print(f"  #{t['rank']} {t['artist']} – {t['title']}")
            print()


if __name__ == "__main__":
    main()
