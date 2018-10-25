from __future__ import print_function
import datetime
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import argparse
from crowbank.petadmin import Environment
# from crowbank.fb_reviews import sql


# If modifying these scopes, delete the file token.json.

CALENDAR_ID = 'cdsmhqnackjcc654qajppqrufs@group.calendar.google.com'

class crowbank_calendar():
    def __init__(self, calendar_id='primary'):
        SCOPES = 'https://www.googleapis.com/auth/calendar'
        store = file.Storage('C:\\Users\\the_y\\token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('C:\\Users\\the_y\\credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        self.service = build('calendar', 'v3', http=creds.authorize(Http()))
        self.id = calendar_id
        #'cdsmhqnackjcc654qajppqrufs@group.calendar.google.com'
        
    def events(self, event_date):
        # return all calendar events of a given date
        timeMin = datetime.datetime.combine(event_date, datetime.datetime.min.time()).isoformat() + 'Z'
        timeMax = datetime.datetime.combine(event_date, datetime.datetime.max.time()).isoformat() + 'Z'
        events_result = self.service.events().list(calendarId=self.id, timeMin=timeMin, timeMax=timeMax,
                                                   singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        return events

    def delete_event(self, event):
        self.service.events().delete(calendarId=self.id, eventId=event['id']).execute()

    def insert_event(self, event_summary, event_desc, event_location, event_start, event_end = None):
        if not event_end:
            event_end = event_start
            
        event = {
            'summary': event_summary,
            'description': event_desc,
            'location': event_location,
            'start': {
                'dateTime': event_start.isoformat(),
                'timeZone': 'Europe/London'
                },
            'end': {
                'dateTime': event_end.isoformat(),
                'timeZone': 'Europe/London'
                 }
            }
        self.service.events().insert(calendarId=self.id, body=event).execute()


def populate_date(env, cal, cal_date):
    events = cal.events(cal_date)
    for event in events:
        cal.delete_event(event)

    cur = env.get_cursor()
    sql = "select cal_time, cal_summary, cal_desc, cal_location from tblcalendar where cal_date='%s'" % cal_date.isoformat()
    cur.execute(sql)
    for row in cur:
        cal.insert_event(row[1], row[2], row[3], datetime.datetime.combine(cal_date, datetime.time.fromisoformat(row[0][:5])))
   

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-date', action='store', help='Date for which to populate google calendar')
    parser.add_argument('-all', action='store_true', help='Populate all future events from database')
    parser.add_argument('-populate', action='store_true', help='Run database populate procedure first')
    
    args = parser.parse_args()

    cal = crowbank_calendar(CALENDAR_ID)
    env = Environment('crowbank_calendar')
    if args.date:
        if args.populate:
            cur = env.get_cursor()
            sql = "execute ppopulate_calendar '%s'" % args.date
            env.execute(sql)
            
        populate_date(env, cal, datetime.date.fromisoformat(args.date))
    
    if args.all:
        if args.populate:
            sql = 'execute ppopulate_calendar_all'
            env.execute(sql)
                    
        cur = env.get_cursor()
        dates = []
        sql = 'select distinct cal_date from tblcalendar where cal_date >= getdate() order by cal_date'
        cur.execute(sql)
        for row in cur:
            dates.append(row[0])
        
        for date in dates:
            populate_date(env, cal, datetime.date.fromisoformat(date))
            

if __name__ == '__main__':
    main()