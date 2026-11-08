from datetime import datetime
from zoneinfo import ZoneInfo
import os
now=datetime.now(ZoneInfo('Europe/Brussels'))
proceed=os.environ.get('GITHUB_EVENT_NAME')!='schedule' or (now.weekday()==0 and now.hour==5)
with open(os.environ['GITHUB_OUTPUT'],'a') as f:
    f.write('proceed='+str(proceed).lower()+'\n')
print('Brussels time:',now,'Run:',proceed)
