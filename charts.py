#!/usr/bin/env python3
"""
Charts Aggregator — FM4, Ö3, Apple Music AT/DE, Electronic Genre Charts.
"""

import requests
import json
import urllib.parse
import time
import re
from html import unescape
from datetime import datetime


# ─── Konfiguration ────────────────────────────────────────────────────────────

ELECTRONIC_GENRES = [
    {"name": "Electronic",  "id": 7},
    {"name": "Dance",       "id": 17},
    {"name": "House",       "id": 1048},
    {"name": "Techno",      "id": 1050},
    {"name": "Trance",      "id": 1051},
    {"name": "Drum & Bass", "id": 1049},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

def get_itunes_info(artist, title, country="at"):
    """Holt Hörprobe und Apple Music App-Link via iTunes Search API."""
    try:
        query = urllib.parse.quote(f"{artist} {title}")
        url = f"https://itunes.apple.com/search?term={query}&media=music&limit=1&country={country}"
        r = requests.get(url, timeout=5)
        results = r.json().get("results", [])
        if results:
            track_url = results[0].get("trackViewUrl", "")
            return {
                "preview_url": results[0].get("previewUrl", ""),
                "app_url": track_url.replace("https://music.apple.com", "music://music.apple.com"),
            }
    except Exception:
        pass
    return {"preview_url": "", "app_url": ""}


def parse_orf_broadcast(program_key, station="fm4"):
    """Holt Songs aus einer ORF-Broadcast-Sendung (FM4 oder Ö3)."""
    r = requests.get(f"https://audioapi.orf.at/{station}/api/json/current/broadcasts", timeout=10)
    data = r.json()
    href = None
    for day in data:
        for b in day.get("broadcasts", []):
            if b.get("programKey") == program_key:
                href = b.get("href")
                break
        if href:
            break
    if not href:
        raise ValueError(f"Keine Sendung '{program_key}' gefunden")
    r2 = requests.get(href, timeout=10)
    items = r2.json().get("items", [])
    seen, rank, tracks = set(), 1, []
    for item in items:
        if item.get("type") == "M" and item.get("interpreter") and item.get("title"):
            key = (item["interpreter"].lower(), item["title"].lower())
            if key not in seen:
                seen.add(key)
                info = get_itunes_info(item["interpreter"], item["title"])
                time.sleep(0.15)
                tracks.append({
                    "rank": rank,
                    "artist": item["interpreter"],
                    "title": item["title"],
                    "preview_url": info["preview_url"],
                    "app_url": info["app_url"],
                })
                rank += 1
                if rank > 25:
                    break
    return tracks


# ─── Datenquellen ─────────────────────────────────────────────────────────────

def get_fm4_charts():
    print("  📻 FM4 Charts...")
    try:
        tracks = parse_orf_broadcast("4CH", "fm4")
        print(f"     {len(tracks)} Songs")
        return tracks
    except Exception as e:
        print(f"     Fehler: {e}")
        return []


def get_oe3_top40():
    print("  📡 Ö3 Austria Top 40...")
    try:
        tracks = parse_orf_broadcast("3TOP", "oe3")
        print(f"     {len(tracks)} Songs")
        return tracks
    except Exception as e:
        print(f"     Fehler: {e}")
        return []


def get_apple_music_charts(country="de"):
    label = {"at": "Österreich 🇦🇹", "de": "Deutschland 🇩🇪"}.get(country, country)
    print(f"  🎵 Apple Music {label}...")
    tracks = []
    try:
        url = f"https://rss.applemarketingtools.com/api/v2/{country}/music/most-played/25/songs.json"
        r = requests.get(url, timeout=10)
        results = r.json().get("feed", {}).get("results", [])
        for i, item in enumerate(results, 1):
            artist = item.get("artistName", "—")
            title = item.get("name", "—")
            info = get_itunes_info(artist, title, country)
            time.sleep(0.15)
            tracks.append({
                "rank": i,
                "artist": artist,
                "title": title,
                "preview_url": info["preview_url"],
                "app_url": info["app_url"],
            })
        print(f"     {len(tracks)} Songs")
    except Exception as e:
        print(f"     Fehler: {e}")
    return tracks


def get_electronic_genre(genre_id, genre_name, country="at", limit=25):
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
            app_url, preview_url = "", ""
            for lnk in links:
                attrs = lnk.get("attributes", {})
                href = attrs.get("href", "")
                if attrs.get("rel") == "alternate" and "music.apple.com" in href:
                    app_url = href.replace("https://music.apple.com", "music://music.apple.com")
                if attrs.get("im:assetType") == "preview":
                    preview_url = href
            tracks.append({"rank": i, "artist": artist, "title": title,
                           "preview_url": preview_url, "app_url": app_url})
    except Exception as e:
        print(f"     Fehler bei {genre_name}: {e}")
    return tracks


def get_all_electronic_charts():
    print("  🎛️  Electronic Genre Charts...")
    result = {}
    for genre in ELECTRONIC_GENRES:
        print(f"     {genre['name']}...")
        result[genre["name"]] = get_electronic_genre(genre["id"], genre["name"])
    return result


# ─── HTML Generierung ─────────────────────────────────────────────────────────

def build_rows(tracks):
    rows = ""
    for t in tracks:
        preview = t.get("preview_url", "")
        app_url = t.get("app_url", "")
        if preview:
            play = f'<button class="play-btn" onclick="togglePlay(this,\'{preview}\')" title="Hörprobe"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></button><audio preload="none"></audio>'
        else:
            play = '<span class="no-play"></span>'
        music = f'<a href="{app_url}" class="music-btn" title="In Apple Music öffnen"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3z"/></svg></a>' if app_url else ""
        rows += f"""<tr>
          <td class="td-rank">{t['rank']}</td>
          <td class="td-play">{play}</td>
          <td class="td-artist">{t['artist']}</td>
          <td class="td-title">{t['title']}</td>
          <td class="td-link">{music}</td>
        </tr>\n"""
    return rows


def build_html(all_data):
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Tab-Definitionen für alle Quellen
    top_tabs = [
        {"id": "fm4",       "label": "FM4",             "icon": "📻"},
        {"id": "oe3",       "label": "Ö3 Top 40",       "icon": "📡"},
        {"id": "apple_at",  "label": "Apple Music AT",  "icon": "🇦🇹"},
        {"id": "apple_de",  "label": "Apple Music DE",  "icon": "🇩🇪"},
        {"id": "electronic","label": "Electronic",       "icon": "🎛️"},
    ]

    tab_btns = ""
    tab_panels = ""

    for i, tab in enumerate(top_tabs):
        active = "active" if i == 0 else ""
        tid = tab["id"]
        tab_btns += f'<button class="top-tab {active}" onclick="switchTab(\'{tid}\')" id="ttab-{tid}">{tab["icon"]} {tab["label"]}</button>'

        if tid == "electronic":
            sub_btns = ""
            sub_panels = ""
            for j, genre in enumerate(ELECTRONIC_GENRES):
                sid = genre["name"].replace(" ", "_").replace("&", "and")
                sa = "active" if j == 0 else ""
                sub_btns += f'<button class="sub-tab {sa}" onclick="switchSub(\'{sid}\')" id="stab-{sid}">{genre["name"]}</button>'
                rows = build_rows(all_data["electronic"].get(genre["name"], []))
                sub_panels += f'<div class="sub-panel {sa}" id="spanel-{sid}"><table><tbody>{rows}</tbody></table></div>'
            panel_content = f'<div class="sub-tab-bar">{sub_btns}</div><div class="sub-panels">{sub_panels}</div>'
        else:
            rows = build_rows(all_data.get(tid, []))
            panel_content = f'<table><tbody>{rows}</tbody></table>'

        tab_panels += f'<div class="top-panel {active}" id="tpanel-{tid}">{panel_content}</div>'

    return f"""<!DOCTYPE html>
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
      --bg:       #f2f2f7;
      --surface:  #ffffff;
      --border:   rgba(0,0,0,0.08);
      --text:     #1c1c1e;
      --sub:      #8e8e93;
      --accent:   #007aff;
      --red:      #ff3b30;
      --rank:     #c7c7cc;
      --radius:   18px;
      --shadow:   0 2px 16px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04);
    }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
    }}

    /* ── Topbar ── */
    .topbar {{
      background: rgba(255,255,255,0.85);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 0 2rem;
    }}
    .topbar-inner {{
      max-width: 900px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      gap: 2rem;
      height: 56px;
    }}
    .logo {{
      font-size: 1rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      white-space: nowrap;
      color: var(--text);
    }}
    .logo span {{ color: var(--accent); }}
    .updated-badge {{
      font-size: 0.7rem;
      color: var(--sub);
      background: var(--bg);
      padding: 0.2rem 0.6rem;
      border-radius: 20px;
      white-space: nowrap;
    }}

    /* ── Top Tabs ── */
    .top-tab-bar {{
      display: flex;
      gap: 0;
      overflow-x: auto;
      scrollbar-width: none;
    }}
    .top-tab-bar::-webkit-scrollbar {{ display: none; }}
    .top-tab {{
      background: none;
      border: none;
      border-bottom: 2.5px solid transparent;
      color: var(--sub);
      padding: 0 1rem;
      height: 56px;
      cursor: pointer;
      font-size: 0.82rem;
      font-weight: 500;
      font-family: 'Inter', sans-serif;
      white-space: nowrap;
      transition: color 0.18s, border-color 0.18s;
      letter-spacing: -0.01em;
    }}
    .top-tab:hover {{ color: var(--text); }}
    .top-tab.active {{
      color: var(--accent);
      border-bottom-color: var(--accent);
    }}

    /* ── Content ── */
    .content {{
      max-width: 900px;
      margin: 0 auto;
      padding: 2rem;
    }}
    .top-panel {{ display: none; animation: fadeIn 0.2s ease; }}
    .top-panel.active {{ display: block; }}

    @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(6px); }} to {{ opacity:1; transform:none; }} }}

    /* ── Sub Tabs (Electronic) ── */
    .sub-tab-bar {{
      display: flex;
      gap: 0.4rem;
      margin-bottom: 1.2rem;
      flex-wrap: wrap;
    }}
    .sub-tab {{
      background: var(--surface);
      border: none;
      color: var(--sub);
      padding: 0.4rem 1rem;
      border-radius: 20px;
      cursor: pointer;
      font-size: 0.78rem;
      font-weight: 500;
      font-family: 'Inter', sans-serif;
      transition: background 0.15s, color 0.15s, transform 0.15s;
      box-shadow: var(--shadow);
    }}
    .sub-tab:hover {{ color: var(--text); transform: scale(1.03); }}
    .sub-tab.active {{ background: var(--accent); color: #fff; }}
    .sub-panel {{ display: none; animation: fadeIn 0.18s ease; }}
    .sub-panel.active {{ display: block; }}

    /* ── Section Header ── */
    .section-header {{
      display: flex;
      align-items: baseline;
      gap: 0.6rem;
      margin-bottom: 1rem;
    }}
    .section-title {{
      font-size: 1.4rem;
      font-weight: 700;
      letter-spacing: -0.03em;
    }}
    .section-sub {{
      font-size: 0.78rem;
      color: var(--sub);
      font-weight: 400;
    }}

    /* ── Tabelle ── */
    .card {{
      background: var(--surface);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    tr {{ transition: background 0.12s; }}
    tr:not(:last-child) td {{ border-bottom: 1px solid var(--border); }}
    tr:hover {{ background: #f9f9fb; }}
    td {{ padding: 0.65rem 0.75rem; vertical-align: middle; }}

    .td-rank {{
      width: 36px;
      font-size: 0.7rem;
      font-weight: 600;
      color: var(--rank);
      text-align: right;
      padding-right: 0.5rem;
    }}
    .td-play {{ width: 40px; }}
    .td-artist {{
      width: 30%;
      font-size: 0.82rem;
      color: var(--sub);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 180px;
    }}
    .td-title {{
      font-size: 0.88rem;
      font-weight: 500;
      letter-spacing: -0.01em;
    }}
    .td-link {{ width: 44px; text-align: right; padding-right: 0.75rem; }}

    /* ── Play Button ── */
    .play-btn {{
      width: 30px; height: 30px;
      border-radius: 50%;
      border: none;
      background: var(--bg);
      color: var(--accent);
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
      flex-shrink: 0;
    }}
    .play-btn svg {{ width: 14px; height: 14px; }}
    .play-btn:hover {{
      background: var(--accent);
      color: #fff;
      transform: scale(1.12);
      box-shadow: 0 4px 14px rgba(0,122,255,0.3);
    }}
    .play-btn.playing {{
      background: var(--accent);
      color: #fff;
      animation: pulsate 1.6s ease infinite;
    }}
    @keyframes pulsate {{
      0%,100% {{ box-shadow: 0 0 0 0 rgba(0,122,255,0.4); }}
      50%      {{ box-shadow: 0 0 0 7px rgba(0,122,255,0); }}
    }}
    .no-play {{ display: inline-block; width: 30px; }}

    /* ── Music Link ── */
    .music-btn {{
      display: inline-flex; align-items: center; justify-content: center;
      width: 30px; height: 30px;
      border-radius: 50%;
      background: var(--bg);
      color: var(--red);
      text-decoration: none;
      transition: background 0.15s, transform 0.15s;
    }}
    .music-btn svg {{ width: 14px; height: 14px; }}
    .music-btn:hover {{
      background: var(--red);
      color: #fff;
      transform: scale(1.12);
    }}

    /* ── Nowplaying Bar ── */
    #nowplaying {{
      position: fixed;
      bottom: 0; left: 0; right: 0;
      background: rgba(255,255,255,0.92);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-top: 1px solid var(--border);
      padding: 0.75rem 2rem;
      display: none;
      align-items: center;
      gap: 1rem;
      z-index: 200;
      animation: slideUp 0.25s ease;
    }}
    #nowplaying.visible {{ display: flex; }}
    @keyframes slideUp {{ from {{ transform: translateY(100%); }} to {{ transform: none; }} }}
    #np-dot {{
      width: 8px; height: 8px;
      border-radius: 50%;
      background: var(--accent);
      animation: pulsate 1.6s ease infinite;
      flex-shrink: 0;
    }}
    #np-text {{
      font-size: 0.82rem;
      font-weight: 500;
      letter-spacing: -0.01em;
      flex: 1;
    }}
    #np-stop {{
      background: none;
      border: none;
      font-size: 1.1rem;
      cursor: pointer;
      color: var(--sub);
      padding: 0.2rem 0.4rem;
      border-radius: 6px;
      transition: color 0.15s, background 0.15s;
    }}
    #np-stop:hover {{ color: var(--red); background: #fff0ef; }}
  </style>
</head>
<body>

  <div class="topbar">
    <div class="topbar-inner">
      <div class="logo">Charts<span>.</span></div>
      <span class="updated-badge">↻ {now}</span>
      <nav class="top-tab-bar" style="margin-left:auto">
        {tab_btns}
      </nav>
    </div>
  </div>

  <div class="content">
    {tab_panels}
  </div>

  <div id="nowplaying">
    <div id="np-dot"></div>
    <div id="np-text">–</div>
    <button id="np-stop" onclick="stopAll()" title="Stop">⏹</button>
  </div>

  <script>
    let curAudio = null, curBtn = null, curArtist = '', curTitle = '';

    function stopAll() {{
      if (curAudio) {{
        curAudio.pause(); curAudio.currentTime = 0;
        curBtn.classList.remove('playing');
        curBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
        curAudio = null; curBtn = null;
      }}
      document.getElementById('nowplaying').classList.remove('visible');
    }}

    function togglePlay(btn, url) {{
      if (curAudio && curBtn === btn) {{ stopAll(); return; }}
      if (curAudio) {{
        curAudio.pause(); curAudio.currentTime = 0;
        curBtn.classList.remove('playing');
        curBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
      }}
      const audio = btn.nextElementSibling;
      audio.src = url;
      audio.play();
      btn.classList.add('playing');
      btn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';
      curAudio = audio; curBtn = btn;

      const row = btn.closest('tr');
      const artist = row.querySelector('.td-artist')?.textContent.trim() || '';
      const title  = row.querySelector('.td-title')?.textContent.trim() || '';
      document.getElementById('np-text').textContent = artist ? artist + ' – ' + title : title;
      document.getElementById('nowplaying').classList.add('visible');

      audio.onended = () => stopAll();
    }}

    function switchTab(id) {{
      document.querySelectorAll('.top-panel').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.top-tab').forEach(b => b.classList.remove('active'));
      document.getElementById('tpanel-' + id).classList.add('active');
      document.getElementById('ttab-' + id).classList.add('active');
      stopAll();
    }}

    function switchSub(id) {{
      document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.sub-tab').forEach(b => b.classList.remove('active'));
      document.getElementById('spanel-' + id).classList.add('active');
      document.getElementById('stab-' + id).classList.add('active');
      stopAll();
    }}
  </script>
</body>
</html>"""


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== Charts Aggregator ===\n")
    print("Lade alle Quellen...\n")

    all_data = {
        "fm4":       get_fm4_charts(),
        "oe3":       get_oe3_top40(),
        "apple_at":  get_apple_music_charts("at"),
        "apple_de":  get_apple_music_charts("de"),
        "electronic": get_all_electronic_charts(),
    }

    print("\nErstelle charts.html...")
    html = build_html(all_data)
    with open("charts.html", "w", encoding="utf-8") as f:
        f.write(html)

    total = sum(len(v) for v in all_data.values() if isinstance(v, list))
    total += sum(len(t) for t in all_data["electronic"].values())
    print(f"\n✅ Fertig! {total} Songs geladen.")
    print("   Öffne charts.html in deinem Browser.\n")


if __name__ == "__main__":
    main()
