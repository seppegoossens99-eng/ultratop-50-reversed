# Ultratop 50 Vlaanderen · Reversed

De volledige Ultratop 50 van #50 naar #1, met dezelfde mobiele weergave als Billboard: zoekveld, kleurlegende, gouden ongewijzigde posities, weekstatistieken, artiestenfoto's, herkomst, leeftijd, genre, debuutjaar en bandleden met rollen en leeftijden.

De website vermeldt de datum van de gebruikte hitlijst. De bron is de bestaande aCharts-weergave van Ultratop Vlaanderen. De parser weigert een onvolledige, toekomstige of verouderde hitlijst. Ontbrekende of onzekere metadata wordt expliciet aangeduid; releasedata blijven voorlopig totdat de oorspronkelijke officiële uitgave is bevestigd.

Automatische update: maandag rond 05:00 Europe/Brussels. GitHub Actions kan de start vertragen. Website en Spotify worden onafhankelijk uitgevoerd; een Spotify-matchprobleem blokkeert de website niet. Handmatig starten werkt standaard alleen de website bij; vink `update_spotify` aan voor beide.

Spotify wordt alleen vervangen wanneer alle 50 nummers betrouwbaar en uniek gekoppeld zijn. Voor ‘Movin’ To The Sun’ is het vastgestelde creditverschil expliciet ondersteund: de hitlijst noemt HUGEL, Imael Angel en Ultra Naté, terwijl Spotify HUGEL en Ultra Naté vermeldt. Die uitzondering geldt alleen voor dit nummer en deze combinatie van credits. De bestaande GitHub-secrets worden hiervoor gebruikt.

Als de bron tijdelijk een foutpagina zonder hitlijst geeft, wordt na drie pogingen uitsluitend een eerder opgeslagen, volledig gevalideerde hitlijst van maximaal zes dagen oud gebruikt. Een oudere, onvolledige of toekomstige snapshot wordt geweigerd; de bestaande playlist blijft dan intact. De gebruikte chartdatum staat steeds in de workflowlog.

Lokaal: installeer requirements.txt en voer `python refresh_project.py` uit. Controles: `python -m unittest test_ultratop_project.py test_chart_source.py test_spotify_update.py`.
