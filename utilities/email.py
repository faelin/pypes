import smtplib
from email.message import EmailMessage
from tempfile import TemporaryFile
from socket import gethostname
import re

from ICPSR.utilities.typing import PathLike

def sendmsg(destination, source, subject, message:str, message_file:PathLike = None, port=25):
    # import smtplib
    msg = EmailMessage()

    if message_file:
        with open(message_file) as message:
            msg.set_content(message.read())
    else:
        msg.set_content(message)

    msg['Subject'] = subject
    msg['From'] = source
    msg['To'] = destination

    if re.match('login6[45].icpsr.umich.edu', gethostname()):
        mailfile = TemporaryFile(dir='/isilon/priv-linux/privmailqueue')
        mailfile.write(msg.as_bytes())
    else:
        s = smtplib.SMTP(f'localhost:{port}')
        s.sendmail(source, [destination], msg.as_string())
        s.quit()