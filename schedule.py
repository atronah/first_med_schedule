import sys
import requests
import logging
from datetime import datetime, timedelta

from icalendar import Calendar, Timezone, TimezoneStandard, Event
from lxml import html

group_id = sys.argv[1]
schedule_url = f'http://www.1spbgmu.ru/ruz/?timetable&group={group_id}'

html_source = requests.get(schedule_url).text

schedule = html.fromstring(html_source)

cal = Calendar()

# timezone info
tz = Timezone()
tz.add('TZID', '(UTC+03:00) Moscow, St. Petersburg, Volgograd')
tz_st = TimezoneStandard()
tz_st.add('DTSTART', datetime(1601, 1, 1))
tz_st.add('TZOFFSETFROM', timedelta(hours=4))
tz_st.add('TZOFFSETTO', timedelta(hours=3))
tz.add_component(tz_st)
cal.add_component(tz)

h4 = schedule.xpath("//h4")
group_name = h4[0].text if h4 else group_id
p_status = schedule.xpath("//p[contains(@class, 'status')]")
status = p_status[0].text if p_status else 'unknown status'

for day_info in schedule.xpath("//div[contains(@class, 'list')]"):
    day_of_week_node = day_info.xpath("*[contains(@class, 'dayofweek')]")
    try:
        event_date = datetime.strptime(day_of_week_node[0].text.split(',')[1].strip()
                                       , '%d.%m.%Y').date()
    except (IndexError, ValueError):
        logging.warning(f'Incorrect day of week info: {day_of_week_node}')
        continue

    for event_info in day_info.xpath("*[contains(@class, 'timetable_sheet')"
                                     " and contains(@class, 'visible')]"):
        event = Event()
        event.add('DTSTAMP', datetime.now())

        time_interval = event_info.xpath("span[contains(@class, 'time_para')]")[0].text
        event_start, event_end = map(lambda s: datetime.strptime(s.strip(), '%H:%M').time(),
                                     time_interval.split('–'))
        event.add('DTSTART', datetime.combine(event_date, event_start))
        event.add('DTEND', datetime.combine(event_date, event_end))
        event.add('LOCATION', event_info.xpath("span[contains(@class, 'auditorium')]")[0].text)
        event.add('SUMMARY', event_info.xpath("span[contains(@class, 'discipline')]")[0].text)

        kind = event_info.xpath("span[contains(@class, 'kindOfWork')]")[0].text
        lecturer = event_info.xpath("span[contains(@class, 'lecturer')]")[0].text
        group_info = event_info.xpath("span[contains(@class, 'group')]")
        group = group_info[0].text if group_info else ''
        event.add('DESCRIPTION',
                  '\n'.join([kind, lecturer, group]))
        event.add('COMMENT', status)
        cal.add_component(event)

with open(f'{group_id}.ics', 'w+b') as ics:
    ics.write(cal.to_ical())


with open('index.html', 'w', encoding='utf-8') as html:
    html.write(
f'''
<!DOCTYPE html>
<head>
    <meta charset="utf-8">
</head>
<body>
    <ul>
        <li>
            <a href="{group_id}.ics">{group_name}</a> ({status})
        </li>
    </ul>
</body>
'''
    )
