"""Refresh public Ultratop chart and artist metadata; does not access Spotify credentials."""
import os
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(Path(__file__).resolve().parent)
if '--finalize' in sys.argv:
    import enrich_artist_extras
    enrich_artist_extras.main()
    import metadata_quality_report
    metadata_quality_report.main()
    import build_mobile_page
    build_mobile_page.main()
    import shutil
    shutil.copyfile('ultratop_50.html','index.html')
    raise SystemExit(0)
import chart_source
chart = chart_source.load_chart()
print('CHART',chart['date'],len(chart['data']),flush=True)
import generate_details
import prefetch_identities
prefetch_identities.main()
generate_details.main(chart)
import collect_band_members
collect_band_members.main()
import enrich_band_members
enrich_band_members.main()
import collect_artist_profiles
collect_artist_profiles.main()
import enrich_artist_extras
enrich_artist_extras.main()
import enrich_catalog
enrich_catalog.main()
import metadata_quality_report
metadata_quality_report.main()
import build_mobile_page
build_mobile_page.main()
import shutil
shutil.copyfile('ultratop_50.html','index.html')
