# https://services.datafordeler.dk/Matriklen2/Matrikel/2.0.0/rest/SamletFastEjendom?SFEBFEnr=xxxxxxx&username=xxx&password=yyy
from BoundingBoxFetching import get_address_object, get_bounding_box_for_address, get_bounding_box_for_address_wgs84
import os
from dotenv import load_dotenv
import requests
import xmltodict

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

def get_building_from_address(address):
    # Get matrikelnr and ejerlavnr
    bbox = get_bounding_box_for_address_wgs84(address)

    type = "Bygning"
    url = f"https://services.datafordeler.dk/GeoDanmarkVektor/GeoDanmark60_NOHIST_GML3/1.0.0/WFS?username={DATAFORDELER_BRUGER}&password={DATAFORDELER_PASSWORD}&service=WFS&request=getfeature&typename={type}&Version=1.1.0&BBOX={bbox}&maxFeatures=1"

    response = requests.get(url)
    response.raise_for_status()

    if not response.content:
        return {"error": "Bygning not found."}

    return xmltodict.parse(response.content)

def get_height_from_model(x, y):
    """Returns the height of the model. x and y must be in EPSG:25832."""
    height_model_api_url = f"https://services.datafordeler.dk/DHMTerraen/DHMKoter/1.0.0/GEOREST/HentKoter?geop=POINT({str(x)} {str(y)})&username={DATAFORDELER_BRUGER}&password={DATAFORDELER_PASSWORD}"
    response = requests.get(height_model_api_url)
    data = response.json()

    if not data:
        return {"error": "Height data not found."}

    return data["HentKoterRespons"]["data"][0]["kote"]