"""Explicit chart-artist identities for ambiguous names; never select a namesake."""
VERIFIED_ARTIST_IDS = {
    'MAKSIM': '3e17154a-7c4a-4560-81ef-af97b3475d3e',
    'Babet': 'b64122e2-5d29-42da-9c39-ddf8cb239553',
    'Sam Harper': '189f1f97-5a0f-4afd-95ec-21ba3afb58a9',
    'Line De Dauw': 'e2e13082-ed4d-4ab6-a121-326bc46f28d4',
    'Bart Kaëll': 'b0aa4a2c-c234-4e6a-bdc9-c092b9b519e2',
    'Justė': 'a0cf2733-ce5a-4b1f-aad6-fd0800a4b2c2',
    'Ed Sheeran': 'b8a7c51f-362c-4dcb-a259-bc6e0095f0a6',
    'Ultra Naté': '0004537a-4b12-43eb-a023-04009e738d2e',
    'DJ Goja': 'ba5d78cb-4419-40c4-8b16-5e3a41254456',
    '54 Ultra': '6f4926ae-865e-483b-86f9-9ae3b9584507',
    'Olivia Dean': '15e0d608-0869-429b-898d-3d8db3ecedd5',
    'Ray Dalton': '6c7f57c4-8f11-4c59-9d63-bca189f343c1',
    'Alex Warren': '609a2ea3-f446-4e31-8eef-9f7591afb55a',
    'Used': '7a32d37d-41e7-4075-95d7-4672c6fe002a',
    'Faithless': '23d9d74d-c95e-46a6-be26-a6075c49747a',
    'The Bausa': '34739a84-b388-4cea-9e77-2609fadd8bb7',
    'Suzan & Freek': 'c0f1c9e6-8b9a-4510-96c6-b8131d78aef9',
    'ANOTR': '5f3be62e-d166-453e-a3ea-07b9227fafae',
    'Kris Kross Amsterdam': 'e90b7b86-7930-4e67-a9c2-806171d11ac4',
    'Swedish House Mafia': '99075985-0d80-4692-a15e-b16f78831792',
    'Steve Lacy': 'b29020d6-5dbf-4c99-b16f-c009f8a712ff',
    'boa': 'ca1dcba2-792c-4550-abf2-7b45396e81ca',
    'Justice': '860b2707-6153-4e3a-aa57-74d2b42c55b5',
}
import json
from pathlib import Path
resolved=Path(__file__).resolve().parent/'resolved_identities.json'
if resolved.exists():
    VERIFIED_ARTIST_IDS.update(json.loads(resolved.read_text(encoding='utf-8')))
