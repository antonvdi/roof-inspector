# https://services.datafordeler.dk/Matriklen2/Matrikel/2.0.0/rest/SamletFastEjendom?SFEBFEnr=xxxxxxx&username=xxx&password=yyy
from BoundingBoxFetching import get_address_object
import os
from dotenv import load_dotenv
import requests

load_dotenv()

DATAFORDELER_PASSWORD = os.getenv('DATAFORDELER_PASSWORD') 
DATAFORDELER_BRUGER = os.getenv('DATAFORDELER_BRUGER')

def get_matrikel_from_address(address):
    """
    Fetches matrikel data from the DAWA API for a given address.
    To get the geometry of the matrikel: features[0]["geometry"]["coordinates"]
    To get the crs: features[0]["geometry"]["crs"]["properties"]["name"]
    """

    # Get matrikelnr and ejerlavnr
    address_object = get_address_object(address)
    matrikel_nr = address_object["adgangsadresse"]["matrikelnr"]
    ejerlav_nr = address_object["adgangsadresse"]["ejerlav"]["kode"]

    matrikel_api_url = f"https://dawa.aws.dk/jordstykker?ejerlavkode={ejerlav_nr}&matrikelnr={matrikel_nr}&format=geojson&srid=25832&noformat&cache=no-cache"
    response = requests.get(matrikel_api_url)
    data = response.json()

    if not data:
        return {"error": "Matrikel not found."}

    return data