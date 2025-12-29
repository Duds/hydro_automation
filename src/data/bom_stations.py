"""BOM (Bureau of Meteorology) observation station database."""

from typing import Dict, List, Tuple, Optional
import math


# BOM Observation Station Database
# Format: station_id: (name, latitude, longitude, state)
BOM_STATIONS: Dict[str, Tuple[str, float, float, str]] = {
    # New South Wales
    "94768": ("Sydney Observatory Hill", -33.8597, 151.2053, "NSW"),
    "94767": ("Sydney Airport", -33.9399, 151.1753, "NSW"),
    "94765": ("Canterbury Racecourse", -33.9047, 151.1100, "NSW"),
    "94755": ("Parramatta North", -33.8000, 151.0000, "NSW"),
    "94752": ("Bankstown Airport", -33.9244, 150.9883, "NSW"),
    "94750": ("Camden Airport", -34.0400, 150.6869, "NSW"),
    "94746": ("Richmond RAAF", -33.6006, 150.7808, "NSW"),
    "94744": ("Penrith Lakes", -33.7167, 150.6833, "NSW"),
    "94726": ("Newcastle Nobbys", -32.9200, 151.7900, "NSW"),
    "94719": ("Williamtown RAAF", -32.7944, 151.8344, "NSW"),
    "94710": ("Cessnock Airport", -32.7875, 151.3422, "NSW"),
    "94703": ("Scone Airport", -32.0372, 150.8322, "NSW"),
    "94693": ("Tamworth Airport", -31.0839, 150.8467, "NSW"),
    "94685": ("Coonabarabran", -31.3333, 149.2667, "NSW"),
    "94672": ("Dubbo", -32.2167, 148.5833, "NSW"),
    "94659": ("Orange Airport", -33.3817, 149.1331, "NSW"),
    "94653": ("Bathurst Airport", -33.4056, 149.6519, "NSW"),
    "94646": ("Katoomba", -33.7167, 150.2833, "NSW"),
    "94637": ("Wagga Wagga", -35.1667, 147.4667, "NSW"),
    "94629": ("Albury Airport", -36.0678, 146.9581, "NSW"),
    "94612": ("Griffith Airport", -34.2503, 146.0669, "NSW"),
    "94604": ("Cobar", -31.5000, 145.8000, "NSW"),
    "94599": ("Broken Hill", -31.9500, 141.4500, "NSW"),
    "94594": ("Wollongong", -34.4333, 150.8833, "NSW"),
    "94578": ("Nowra", -34.9500, 150.7000, "NSW"),
    "94568": ("Moruya Airport", -35.9083, 150.1444, "NSW"),
    "94563": ("Merimbula Airport", -36.9086, 149.9014, "NSW"),
    
    # Victoria
    "95936": ("Melbourne", -37.8136, 144.9631, "VIC"),
    "95904": ("Melbourne Airport", -37.6733, 144.8433, "VIC"),
    "95871": ("Avalon Airport", -38.0394, 144.4694, "VIC"),
    "95866": ("Geelong", -38.1500, 144.3500, "VIC"),
    "95832": ("Ballarat", -37.5000, 143.8167, "VIC"),
    "95829": ("Bendigo", -36.7500, 144.2833, "VIC"),
    "95816": ("Mildura Airport", -34.2356, 142.0867, "VIC"),
    "95805": ("Swan Hill", -35.3333, 143.5500, "VIC"),
    "95796": ("Shepparton", -36.3833, 145.4000, "VIC"),
    "95787": ("Albury", -36.0667, 146.9500, "VIC"),
    "95778": ("Wodonga", -36.1000, 146.8833, "VIC"),
    "95766": ("Wangaratta", -36.3500, 146.3000, "VIC"),
    "95753": ("Mount Hotham", -37.0500, 147.1333, "VIC"),
    "95736": ("Horsham", -36.6667, 142.1667, "VIC"),
    "95726": ("Hamilton", -37.6500, 142.0667, "VIC"),
    "95716": ("Warrnambool", -38.2833, 142.4333, "VIC"),
    "95704": ("Portland", -38.3500, 141.6167, "VIC"),
    "95696": ("Cape Otway", -38.8500, 143.5167, "VIC"),
    "95687": ("Aireys Inlet", -38.4667, 144.1000, "VIC"),
    "95677": ("Laverton RAAF", -37.8633, 144.7461, "VIC"),
    "95666": ("Essendon Airport", -37.7281, 144.9019, "VIC"),
    "95635": ("Mount Dandenong", -37.8333, 145.3500, "VIC"),
    "95624": ("Coldstream", -37.7167, 145.3833, "VIC"),
    
    # Queensland
    "94578": ("Brisbane", -27.4698, 153.0251, "QLD"),
    "94576": ("Brisbane Airport", -27.3842, 153.1175, "QLD"),
    "94568": ("Amberley AMO", -27.6333, 152.7167, "QLD"),
    "94564": ("Beaudesert", -27.9833, 153.0000, "QLD"),
    "94552": ("Gold Coast", -28.1667, 153.5000, "QLD"),
    "94542": ("Coolangatta", -28.1667, 153.5000, "QLD"),
    "94527": ("Toowoomba", -27.5500, 151.9167, "QLD"),
    "94510": ("Warwick", -28.2167, 152.0000, "QLD"),
    "94494": ("Ipswich", -27.6167, 152.7667, "QLD"),
    "94481": ("Gatton", -27.5500, 152.3333, "QLD"),
    "94461": ("Gympie", -26.1833, 152.7000, "QLD"),
    "94448": ("Maryborough", -25.5167, 152.7167, "QLD"),
    "94430": ("Bundaberg", -24.9000, 152.3167, "QLD"),
    "94420": ("Gladstone", -23.8500, 151.2667, "QLD"),
    "94403": ("Rockhampton", -23.3833, 150.4833, "QLD"),
    "94387": ("Mackay", -21.1167, 149.2167, "QLD"),
    "94374": ("Proserpine Airport", -20.4950, 148.5522, "QLD"),
    "94367": ("Bowen", -20.0167, 148.2333, "QLD"),
    "94360": ("Townsville", -19.2500, 146.7667, "QLD"),
    "94346": ("Cairns", -16.8833, 145.7500, "QLD"),
    "94335": ("Cooktown", -15.4667, 145.2500, "QLD"),
    "94326": ("Weipa", -12.6833, 141.9167, "QLD"),
    "94312": ("Mount Isa", -20.6833, 139.4833, "QLD"),
    "94300": ("Longreach", -23.4333, 144.2833, "QLD"),
    "94287": ("Charleville", -26.4167, 146.2500, "QLD"),
    "94275": ("Roma", -26.5500, 148.7833, "QLD"),
    "94258": ("St George", -28.0333, 148.5833, "QLD"),
    "94248": ("Goondiwindi", -28.5500, 150.3167, "QLD"),
    "94238": ("Dalby", -27.1833, 151.2667, "QLD"),
    "94229": ("Oakey", -27.4167, 151.7333, "QLD"),
    
    # Western Australia
    "94610": ("Perth", -31.9505, 115.8605, "WA"),
    "94608": ("Perth Airport", -31.9383, 115.9669, "WA"),
    "94601": ("Jandakot Airport", -32.0975, 115.8811, "WA"),
    "94599": ("Rottnest Island", -32.0000, 115.5000, "WA"),
    "94592": ("Geraldton", -28.8000, 114.7000, "WA"),
    "94578": ("Carnarvon", -24.8833, 113.6667, "WA"),
    "94568": ("Exmouth", -21.9333, 114.1167, "WA"),
    "94558": ("Learmonth", -22.2333, 114.0833, "WA"),
    "94548": ("Port Hedland", -20.3667, 118.6167, "WA"),
    "94538": ("Karratha", -20.7167, 116.7667, "WA"),
    "94528": ("Broome", -17.9500, 122.2167, "WA"),
    "94518": ("Halls Creek", -18.2333, 127.6667, "WA"),
    "94508": ("Kununurra", -15.7833, 128.7167, "WA"),
    "94498": ("Kalgoorlie", -30.7833, 121.4500, "WA"),
    "94488": ("Esperance", -33.8333, 121.8833, "WA"),
    "94478": ("Albany", -35.0333, 117.8833, "WA"),
    "94468": ("Bunbury", -33.3333, 115.6333, "WA"),
    "94458": ("Busselton", -33.6833, 115.4000, "WA"),
    "94448": ("Mandurah", -32.5333, 115.7167, "WA"),
    "94438": ("Bunbury", -33.3333, 115.6333, "WA"),
    
    # South Australia
    "94672": ("Adelaide", -34.9285, 138.6007, "SA"),
    "94668": ("Adelaide Airport", -34.9450, 138.5306, "SA"),
    "94659": ("Parafield Airport", -34.7933, 138.6331, "SA"),
    "94653": ("Edinburgh RAAF", -34.7025, 138.6208, "SA"),
    "94646": ("Mount Lofty", -34.9667, 138.7000, "SA"),
    "94637": ("Noarlunga", -35.1500, 138.4833, "SA"),
    "94626": ("Kuitpo", -35.1667, 138.6833, "SA"),
    "94619": ("Strathalbyn", -35.2667, 138.9000, "SA"),
    "94610": ("Murray Bridge", -35.1167, 139.3333, "SA"),
    "94603": ("Renmark", -34.1667, 140.7500, "SA"),
    "94596": ("Berri", -34.2833, 140.6000, "SA"),
    "94588": ("Loxton", -34.4500, 140.5833, "SA"),
    "94578": ("Kadina", -33.9667, 137.7167, "SA"),
    "94568": ("Whyalla", -33.0500, 137.5167, "SA"),
    "94558": ("Port Augusta", -32.5000, 137.7667, "SA"),
    "94548": ("Ceduna", -32.1333, 133.7000, "SA"),
    "94538": ("Woomera", -31.1667, 136.8167, "SA"),
    "94528": ("Coober Pedy", -29.0333, 134.7167, "SA"),
    "94518": ("Mount Gambier", -37.7500, 140.7667, "SA"),
    "94508": ("Naracoorte", -36.9500, 140.7333, "SA"),
    
    # Tasmania
    "94995": ("Hobart", -42.8806, 147.3250, "TAS"),
    "94996": ("Hobart Airport", -42.8361, 147.5103, "TAS"),
    "94975": ("Launceston", -41.4333, 147.1333, "TAS"),
    "94968": ("Launceston Airport", -41.5453, 147.2142, "TAS"),
    "94957": ("Devonport", -41.1833, 146.3500, "TAS"),
    "94947": ("Burnie", -41.0500, 145.9000, "TAS"),
    "94937": ("Strahan", -42.1500, 145.2833, "TAS"),
    "94926": ("Queenstown", -42.0833, 145.5500, "TAS"),
    "94916": ("Cape Bruny", -43.5000, 147.1500, "TAS"),
    "94907": ("Cape Sorell", -42.2000, 145.1833, "TAS"),
    "94896": ("King Island", -39.9333, 143.8667, "TAS"),
    "94887": ("Flinders Island", -40.0833, 148.0167, "TAS"),
    
    # Northern Territory
    "94120": ("Darwin", -12.4167, 130.8833, "NT"),
    "94112": ("Darwin Airport", -12.4147, 130.8767, "NT"),
    "94107": ("Batchelor", -13.0500, 131.0167, "NT"),
    "94102": ("Adelaide River", -13.2333, 131.1167, "NT"),
    "94097": ("Katherine", -14.4667, 132.2667, "NT"),
    "94087": ("Tennant Creek", -19.6333, 134.1833, "NT"),
    "94077": ("Alice Springs", -23.8000, 133.8833, "NT"),
    "94067": ("Yulara", -25.1833, 130.9833, "NT"),
    "94057": ("Nhulunbuy", -12.1833, 136.7833, "NT"),
    "94047": ("Gove Airport", -12.2694, 136.8183, "NT"),
    "94037": ("Groote Eylandt", -13.9667, 136.4500, "NT"),
    
    # Australian Capital Territory
    "94926": ("Canberra", -35.3075, 149.1244, "ACT"),
    "94910": ("Canberra Airport", -35.3069, 149.1950, "ACT"),
    "94907": ("Tuggeranong", -35.4167, 149.0667, "ACT"),
}


def get_station_info(station_id: str) -> Optional[Tuple[str, float, float, str]]:
    """
    Get station information by ID.
    
    Args:
        station_id: BOM station ID
        
    Returns:
        Tuple of (name, latitude, longitude, state) or None if not found
    """
    return BOM_STATIONS.get(station_id)


def get_station_name(station_id: str) -> Optional[str]:
    """
    Get station name by ID.
    
    Args:
        station_id: BOM station ID
        
    Returns:
        Station name or None if not found
    """
    info = get_station_info(station_id)
    return info[0] if info else None


def find_nearest_station(latitude: float, longitude: float) -> Optional[Tuple[str, str, float]]:
    """
    Find nearest BOM observation station to given coordinates.
    
    Args:
        latitude: Latitude
        longitude: Longitude
        
    Returns:
        Tuple of (station_id, station_name, distance_km) or None if not found
    """
    if not BOM_STATIONS:
        return None
    
    min_distance_km = float('inf')
    closest_station_id = None
    closest_station_name = None
    
    for station_id, (name, lat, lon, state) in BOM_STATIONS.items():
        # Calculate distance using Haversine formula
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat - latitude)
        dlon = math.radians(lon - longitude)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(latitude)) * math.cos(math.radians(lat)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = R * c
        
        if distance_km < min_distance_km:
            min_distance_km = distance_km
            closest_station_id = station_id
            closest_station_name = name
    
    if closest_station_id:
        return (closest_station_id, closest_station_name, min_distance_km)
    
    return None


def get_all_stations() -> List[Dict[str, str]]:
    """
    Get all stations as a list of dictionaries.
    
    Returns:
        List of station dicts with keys: id, name, state
    """
    stations = []
    for station_id, (name, lat, lon, state) in BOM_STATIONS.items():
        stations.append({
            "id": station_id,
            "name": name,
            "state": state,
            "latitude": lat,
            "longitude": lon
        })
    return sorted(stations, key=lambda x: (x["state"], x["name"]))


def search_stations(query: str) -> List[Dict[str, str]]:
    """
    Search stations by name or state.
    
    Args:
        query: Search query (station name or state)
        
    Returns:
        List of matching station dicts
    """
    query_lower = query.lower()
    matches = []
    
    for station_id, (name, lat, lon, state) in BOM_STATIONS.items():
        if (query_lower in name.lower() or 
            query_lower in state.lower() or
            query_lower in station_id):
            matches.append({
                "id": station_id,
                "name": name,
                "state": state,
                "latitude": lat,
                "longitude": lon
            })
    
    return sorted(matches, key=lambda x: (x["state"], x["name"]))

