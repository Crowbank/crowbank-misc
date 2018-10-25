import googlemaps
import argparse
from crowbank.petadmin import Environment

API_KEY = 'AIzaSyDfiBAXrJDolwV_qKETTVqgyUaLgm3SJPc'
CROWBANK_LOC = 'Crowbank House, Arns, Cumbernauld G67 3JW'

def vet_distances():
    env = Environment('prod')
    cur = env.get_cursor()
    
    gmaps = googlemaps.Client(key=API_KEY)
    
    # Geocoding an address
    crowbank_location = 'Crowbank House, Arns, Cumbernauld G67 3JW'
    
    sql = '''select top 20 vet_no, vet_postcode from pa..tblbooking
    join pa..tblbookingitem on bi_bk_no = bk_no join pa..tblpet on pet_no = bi_pet_no and pet_spec_no = 1
    join pa..tblvet on vet_no = pet_vet_no
    where bk_start_date between '20180101' and '20181019' and bk_status in ('', 'V') and vet_postcode <> ''
    group by vet_no, vet_postcode
    order by sum(datediff(day, bk_start_date, bk_end_date)) desc'''
    
    cur.execute(sql)
    
    vet_nos = []
    vet_postcodes = []
    
    for row in cur:
        vet_nos.append(row[0])
        vet_postcodes.append(row[1])
    
    # directions_result = gmaps.directions("Sydney Town Hall",
    #                                      "Parramatta, NSW",
    #                                      mode="transit",
    #                                      departure_time=now)
    
    
    res = gmaps.distance_matrix(crowbank_location, vet_postcodes, mode='driving')
    res = res['rows'][0]['elements']
    
    outp = list(zip([x['duration']['text'] for x in res], [x['duration']['value'] for x in res], vet_nos))
    for v in outp:
        sql = "update tblvetduration set vet_duration = '%s', vet_time = %d where vet_no = %d" % v
        env.execute(sql)


def main():  
    parser = argparse.ArgumentParser()
    parser.add_argument('postcode', action='store', help='Destination Postcode')

    args = parser.parse_args()
    gmaps = googlemaps.Client(key=API_KEY)
    
    res = gmaps.distance_matrix(CROWBANK_LOC, args.postcode, mode='driving')
    res = res['rows'][0]['elements'][0]
    if 'duration' in res:
        duration = res['duration']['text']
        print(duration)
    
if __name__ == '__main__':
    main()