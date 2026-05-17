#!/usr/bin/env python3
"""
Charts Aggregator - FM4, Apple Music, Electronic Genre Charts mit Hörproben.
"""

import requests
import json
import urllib.parse
import time
from datetime import datetime


ELECTRONIC_GENRES = [
    {"name": "Electronic",  "id": 7},
    {"name": "Dance",       "id": 17},
    {"name": "House",       "id": 1048},
    {"name": "Techno",      "id": 1050},
    {"name": "Trance",      "id": 1051},
    {"name": "Drum & Bass", "id": 1049},
]


def get_itunes_info(artist, title, country="at"):
    """Holt Hörprobe und Apple Music App-Link via iTunes Search API."""
    try:
        query = urllib.parse.quote(f"{artist} {title}")
        url = f"https://itunes.apple.com/search?term={query}&media=music&limit=1&country={country}"
        r = requests.get(url, timeout=5)
        results = r.json().get("results", [])
        if results:
            track_url = results[0].get("trackViewUrl", "")
            app_url = track_url.replace("https://music.apple.com", "music://music.apple.com")
            return {
                "preview_url": results[0].get("previewUrl", ""),
                "app_url": app_url,
            }
    except Exception:
        pass
    return {"preview_url": "", "app_url": ""}


def get_fm4_charts():
    """Holt die gespielten Songs aus der FM4 Charts Sendung via ORF API."""
    print("  Lade FM4 Charts...")
    tracks = []
    try:
        r = requests.get("https://audioapi.orf.at/fm4/api/json/current/broadcasts", timeout=10)
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

        r2 = requests.get(chart_href, timeout=10)
        items = r2.json().get("items", [])

        seen = set()
        rank = 1
        for item in items:
            if item.get("type") == "M" and item.get("interpreter") and item.get("title"):
                key = (item["interpreter"].lower(), item["title"].lower())
                if key not in seen:
                    seen.add(key)
                    info = get_itunes_info(item["interpreter"], item["title"])
                    time.sleep(0.2)
                    tracks.append({
                        "rank": rank,
                        "artist": item["interpreter"],
                        "title": item["title"],
                        "preview_url": info["preview_url"],
                        "app_url": info["app_url"],
                    })
                    rank += 1
                    if rank > 20:
                        break
    except Exception as e:
        print(f"  FM4 Fehler: {e}")
    print(f"  {len(tracks)} Songs geladen.")
    return tracks


def get_apple_music_charts(country="de", limit=20):
    """Holt die offiziellen Apple Music Top Songs Charts."""
    label = {"at": "Österreich", "de": "Deutschland"}.get(country, country.upper())
    print(f"  Lade Apple Music Charts {label}...")
    tracks = []
    try:
        url = f"https://rss.applemarketingtools.com/api/v2/{country}/music/most-played/{limit}/songs.json"
        r = requests.get(url, timeout=10)
        results = r.json().get("feed", {}).get("results", [])
        for i, item in enumerate(results, 1):
            artist = item.get("artistName", "—")
            title = item.get("name", "—")
            info = get_itunes_info(artist, title, country)
            time.sleep(0.2)
            tracks.append({
                "rank": i,
                "artist": artist,
                "title": title,
                "preview_url": info["preview_url"],
                "app_url": info["app_url"],
            })
    except Exception as e:
        print(f"  Fehler: {e}")
    print(f"  {len(tracks)} Songs geladen.")
    return tracks


def get_electronic_genre_charts(genre_id, genre_name, country="at", limit=20):
    """Holt iTunes Electronic Genre Charts."""
    print(f"    {genre_name}...")
    tracks = []
    try:
        url = f"https://itunes.apple.com/{country}/rss/topsongs/limit={limit}/genre={genre_id}/json"
        r = requests.get(url, timeout=10)
        entries = r.json().get("feed", {}).get("entry", [])
        for i, entry in enumerate(entries, 1):
            artist = entry.get("im:artist", {}).get("label", "—")
            title = entry.get("im:name", {}).get("label", "—")
            links = entry.get("link", [])
            if isinstance(links, dict):
                links = [links]
            app_url = ""
            preview_url = ""
            for lnk in links:
                attrs = lnk.get("attributes", {})
                href = attrs.get("href", "")
                if attrs.get("rel") == "alternate" and "music.apple.com" in href:
                    app_url = href.replace("https://music.apple.com", "music://music.apple.com")
                if attrs.get("im:assetType") == "preview":
                    preview_url = href
            tracks.append({
                "rank": i,
                "artist": artist,
                "title": title,
                "preview_url": preview_url,
                "app_url": app_url,
            })
    except Exception as e:
        print(f"    Fehler bei {genre_name}: {e}")
    return tracks


def get_all_electronic_charts():
    """Lädt alle Electronic Genre Charts."""
    print("  Lade Electronic Genre Charts...")
    result = {}
    for genre in ELECTRONIC_GENRES:
        result[genre["name"]] = get_electronic_genre_charts(genre["id"], genre["name"])
    return result


def build_chart_rows(tracks):
    rows = ""
    for t in tracks:
        preview = t.get("preview_url", "")
        app_url = t.get("app_url", "")

        if preview:
            preview_btn = f'<button class="preview-btn" onclick="togglePreview(this,\'{preview}\')" title="Hörprobe">&#9654;</button><audio class="preview-audio" preload="none"></audio>'
        else:
            preview_btn = '<span class="no-preview">—</span>'

        apple_btn = f'<a href="{app_url}" class="apple-btn">&#9835; Apple Music</a>' if app_url else ""

        rows += f"""<tr>
          <td class="rank">{t['rank']}</td>
          <td class="preview-cell">{preview_btn}</td>
          <td class="artist">{t['artist']}</td>
          <td class="title">{t['title']}</td>
          <td>{apple_btn}</td>
        </tr>"""
    return rows


def build_html(fm4, apple_de, electronic_genres):
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # FM4 Tabelle
    fm4_table = f"""
    <div class="chart-card">
      <div class="card-header">
        <span class="card-icon">📻</span>
        <div>
          <h2>FM4 Charts</h2>
          <p class="card-sub">Österreichischer Radiosender</p>
        </div>
      </div>
      <table><tbody>{build_chart_rows(fm4)}</tbody></table>
    </div>"""

    # Apple Music DE Tabelle
    apple_table = f"""
    <div class="chart-card">
      <div class="card-header">
        <span class="card-icon">🇩🇪</span>
        <div>
          <h2>Apple Music Deutschland</h2>
          <p class="card-sub">Top Songs gerade</p>
        </div>
      </div>
      <table><tbody>{build_chart_rows(apple_de)}</tbody></table>
    </div>"""

    # Electronic Genre Tabs
    tab_buttons = ""
    tab_panels = ""
    for i, genre in enumerate(ELECTRONIC_GENRES):
        active_btn = "active" if i == 0 else ""
        active_panel = "active" if i == 0 else ""
        safe_id = genre["name"].replace(" ", "_").replace("&", "and")
        tab_buttons += f'<button class="tab-btn {active_btn}" onclick="showTab(\'{safe_id}\')" id="btn-{safe_id}">{genre["name"]}</button>'
        rows = build_chart_rows(electronic_genres.get(genre["name"], []))
        tab_panels += f'<div class="tab-panel {active_panel}" id="panel-{safe_id}"><table><tbody>{rows}</tbody></table></div>'

    electronic_section = f"""
    <div class="chart-card wide">
      <div class="card-header">
        <span class="card-icon">🎛️</span>
        <div>
          <h2>Electronic Charts</h2>
          <p class="card-sub">Top Songs nach Genre · via iTunes</p>
        </div>
      </div>
      <div class="tab-bar">{tab_buttons}</div>
      <div class="tab-content">{tab_panels}</div>
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Charts Aggregator</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:        #f5f5f7;
      --surface:   #ffffff;
      --border:    #e5e5ea;
      --text:      #1d1d1f;
      --sub:       #86868b;
      --accent:    #0071e3;
      --accent-hover: #0077ed;
      --apple-red: #fc3c44;
      --rank:      #c7c7cc;
      --shadow:    0 2px 12px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04);
      --shadow-hover: 0 8px 30px rgba(0,0,0,0.11), 0 2px 8px rgba(0,0,0,0.06);
      --radius:    16px;
      --radius-sm: 10px;
    }}

    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 2.5rem 2rem;
      -webkit-font-smoothing: antialiased;
    }}

    /* Header */
    header {{
      max-width: 1400px;
      margin: 0 auto 2.5rem;
      display: flex;
      align-items: baseline;
      gap: 1.2rem;
      animation: fadeDown 0.5s ease both;
    }}
    @keyframes fadeDown {{
      from {{ opacity: 0; transform: translateY(-12px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}
    h1 {{
      font-size: 2rem;
      font-weight: 700;
      letter-spacing: -0.03em;
      color: var(--text);
    }}
    .updated {{
      font-size: 0.78rem;
      color: var(--sub);
      font-weight: 400;
    }}

    /* Grid */
    .charts-grid {{
      max-width: 1400px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
      gap: 1.5rem;
    }}

    /* Card */
    .chart-card {{
      background: var(--surface);
      border-radius: var(--radius);
      padding: 1.5rem;
      box-shadow: var(--shadow);
      transition: box-shadow 0.25s ease, transform 0.25s ease;
      animation: fadeUp 0.5s ease both;
    }}
    .chart-card:hover {{
      box-shadow: var(--shadow-hover);
      transform: translateY(-2px);
    }}
    .chart-card.wide {{ grid-column: 1 / -1; }}

    @keyframes fadeUp {{
      from {{ opacity: 0; transform: translateY(16px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .chart-card:nth-child(1) {{ animation-delay: 0.05s; }}
    .chart-card:nth-child(2) {{ animation-delay: 0.10s; }}
    .chart-card:nth-child(3) {{ animation-delay: 0.15s; }}

    .card-header {{
      display: flex;
      align-items: center;
      gap: 0.85rem;
      margin-bottom: 1.2rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border);
    }}
    .card-icon {{ font-size: 1.5rem; line-height: 1; }}
    .card-header h2 {{
      font-size: 0.95rem;
      font-weight: 600;
      letter-spacing: -0.01em;
    }}
    .card-sub {{
      font-size: 0.75rem;
      color: var(--sub);
      margin-top: 1px;
      font-weight: 400;
    }}

    /* Tabs */
    .tab-bar {{
      display: flex;
      gap: 0.4rem;
      margin-bottom: 1.1rem;
      flex-wrap: wrap;
    }}
    .tab-btn {{
      background: var(--bg);
      border: none;
      color: var(--sub);
      padding: 0.35rem 0.85rem;
      border-radius: 20px;
      cursor: pointer;
      font-size: 0.78rem;
      font-weight: 500;
      font-family: 'Inter', sans-serif;
      letter-spacing: -0.01em;
      transition: background 0.18s ease, color 0.18s ease, transform 0.15s ease;
    }}
    .tab-btn:hover {{
      background: #e5e5ea;
      color: var(--text);
      transform: scale(1.03);
    }}
    .tab-btn.active {{
      background: var(--accent);
      color: #fff;
      transform: scale(1.0);
    }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; animation: fadeIn 0.2s ease; }}
    @keyframes fadeIn {{
      from {{ opacity: 0; }}
      to   {{ opacity: 1; }}
    }}

    /* Tabelle */
    table {{ width: 100%; border-collapse: collapse; }}
    tr {{
      transition: background 0.15s ease;
      border-radius: var(--radius-sm);
    }}
    tr:not(:last-child) td {{ border-bottom: 1px solid var(--border); }}
    tr:hover {{ background: #f5f5f7; }}
    td {{ padding: 0.6rem 0.5rem; font-size: 0.855rem; vertical-align: middle; }}

    .rank {{
      width: 32px;
      font-size: 0.72rem;
      font-weight: 600;
      color: var(--rank);
      letter-spacing: 0.02em;
    }}
    .preview-cell {{ width: 38px; }}

    .preview-btn {{
      width: 30px; height: 30px;
      border-radius: 50%;
      border: none;
      background: var(--bg);
      color: var(--accent);
      cursor: pointer;
      font-size: 0.65rem;
      display: flex; align-items: center; justify-content: center;
      transition: background 0.18s ease, transform 0.15s ease, box-shadow 0.18s ease;
      flex-shrink: 0;
    }}
    .preview-btn:hover {{
      background: var(--accent);
      color: #fff;
      transform: scale(1.1);
      box-shadow: 0 4px 12px rgba(0,113,227,0.3);
    }}
    .preview-btn.playing {{
      background: var(--accent);
      color: #fff;
      box-shadow: 0 4px 12px rgba(0,113,227,0.35);
      animation: pulse 1.4s ease infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ box-shadow: 0 4px 12px rgba(0,113,227,0.35); }}
      50%       {{ box-shadow: 0 4px 20px rgba(0,113,227,0.55); }}
    }}
    .no-preview {{ color: var(--border); font-size: 0.8rem; padding-left: 6px; }}

    .artist {{
      color: var(--sub);
      font-weight: 400;
      width: 30%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 160px;
    }}
    .title {{
      font-weight: 500;
      color: var(--text);
      letter-spacing: -0.01em;
    }}

    .apple-btn {{
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      background: var(--apple-red);
      color: #fff;
      text-decoration: none;
      padding: 0.25rem 0.75rem;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 500;
      white-space: nowrap;
      font-family: 'Inter', sans-serif;
      transition: opacity 0.15s ease, transform 0.15s ease;
    }}
    .apple-btn:hover {{
      opacity: 0.88;
      transform: scale(1.04);
    }}
  </style>
</head>
<body>
  <header>
    <h1>Charts Aggregator</h1>
    <span class="updated">Aktualisiert: {now}</span>
  </header>

  <div class="charts-grid">
    {fm4_table}
    {apple_table}
    {electronic_section}
  </div>

  <script>
    let currentAudio = null;
    let currentBtn = null;

    function togglePreview(btn, url) {{
      if (currentAudio && currentBtn === btn) {{
        currentAudio.pause();
        currentAudio.currentTime = 0;
        btn.innerHTML = '&#9654;';
        btn.classList.remove('playing');
        currentAudio = null; currentBtn = null;
        return;
      }}
      if (currentAudio) {{
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentBtn.innerHTML = '&#9654;';
        currentBtn.classList.remove('playing');
      }}
      const audio = btn.nextElementSibling;
      audio.src = url;
      audio.play();
      btn.innerHTML = '&#9646;&#9646;';
      btn.classList.add('playing');
      currentAudio = audio; currentBtn = btn;
      audio.onended = () => {{
        btn.innerHTML = '&#9654;';
        btn.classList.remove('playing');
        currentAudio = null; currentBtn = null;
      }};
    }}

    function showTab(id) {{
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('panel-' + id).classList.add('active');
      document.getElementById('btn-' + id).classList.add('active');
      if (currentAudio) {{
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentBtn.innerHTML = '&#9654;';
        currentBtn.classList.remove('playing');
        currentAudio = null; currentBtn = null;
      }}
    }}
  </script>
</body>
</html>"""
    return html


def main():
    print("=== Charts Aggregator ===")
    print()
    print("Lade Charts (dauert ~2 Minuten wegen Hörproben-Suche)...")
    print()

    print("📻 FM4:")
    fm4 = get_fm4_charts()
    print()

    print("🇩🇪 Apple Music DE:")
    apple_de = get_apple_music_charts(country="de", limit=20)
    print()

    print("🎛️ Electronic Genre Charts:")
    electronic = get_all_electronic_charts()
    print()

    print("Erstelle charts.html ...")
    html = build_html(fm4, apple_de, electronic)
    with open("charts.html", "w", encoding="utf-8") as f:
        f.write(html)

    print()
    print("✅ Fertig! Öffne charts.html in deinem Browser.")
    total_songs = len(fm4) + len(apple_de) + sum(len(v) for v in electronic.values())
    with_preview = (
        sum(1 for t in fm4 if t.get("preview_url")) +
        sum(1 for t in apple_de if t.get("preview_url")) +
        sum(1 for v in electronic.values() for t in v if t.get("preview_url"))
    )
    print(f"   {total_songs} Songs insgesamt, {with_preview} mit Hörprobe")


if __name__ == "__main__":
    main()
