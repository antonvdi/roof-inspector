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

def get_height_from_model(x, y):
    """Returns the height of the model. x and y must be in EPSG:25832."""
    height_model_api_url = f"https://services.datafordeler.dk/DHMTerraen/DHMKoter/1.0.0/GEOREST/HentKoter?geop=POINT({str(x)} {str(y)})&username={DATAFORDELER_BRUGER}&password={DATAFORDELER_PASSWORD}"
    response = requests.get(height_model_api_url)
    data = response.json()

    if not data:
        return {"error": "Height data not found."}

    return data["HentKoterRespons"]["data"][0]["kote"]
