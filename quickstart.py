from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/calendar'

def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
#    GCAL = build('calendar', 'v3', http=creds.authorize(Http()))

    # Call the Calendar API
#     now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
#     print('Getting the upcoming 10 events')
#     events_result = service.events().list(calendarId='primary', timeMin=now,
#                                         maxResults=10, singleEvents=True,
#                                         orderBy='startTime').execute()
#     events = events_result.get('items', [])
# 
#     if not events:
#         print('No upcoming events found.')
#     for event in events:
#         start = event['start'].get('dateTime', event['start'].get('date'))
#         print(start, event['summary'])


#     page_token = None
#     while True:
#         calendar_list = GCAL.calendarList().list(pageToken=page_token).execute()
#         for calendar_list_entry in calendar_list['items']:
#             print (calendar_list_entry['summary'])
#         page_token = calendar_list.get('nextPageToken')
#         if not page_token:
#             break

    GCAL = build('calendar', 'v3', http=creds.authorize(Http()))
     
#    GMT_OFF = '+00:00'      # PDT/MST/GMT-7

    events_result = GCAL.events().list(calendarId='cdsmhqnackjcc654qajppqrufs@group.calendar.google.com', timeMin='2018-10-19T00:00:00Z',
                                       timeMax = '2018-10-19T23:59:59Z',
                                        singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    for event in events:
        pass

    EVENT = {
        'summary': 'Working Today',
        'start':  {'dateTime': '2018-10-19T08:00:00', 'timeZone': 'Europe/London'},
        'end':    {'dateTime': '2018-10-19T08:00:00', 'timeZone': 'Europe/London'}
    }
     
    e = GCAL.events().insert(calendarId='cdsmhqnackjcc654qajppqrufs@group.calendar.google.com',
            sendNotifications=True, body=EVENT).execute()
     
     
    print('''*** %r event added:
        Start: %s
        End:   %s''' % (e['summary'].encode('utf-8'),
            e['start']['dateTime'], e['end']['dateTime']))



if __name__ == '__main__':
    main()
