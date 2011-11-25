==========
IMAP Idler
==========
.. highlight:: python

**IMAPIdler** is helper class to easily create IMAP robots with IDLE support.

All you have to do to start using it is in this example::

   from imapidler import IMAPIdler

   def process_message(content):
       print content
       return True

   myidler = IMAPIdler('localhost', 'login', 'secret!', processor=process_message)
   myidler.run()

You can also use inheritance approach::

   from imapidler import IMAPIdler
   
   class MyIMAPIdler(IMAPIdler):
       def process_message(self, content):
           print content
           return True

   myidler = MyIMAPIdler('localhost', 'login', 'secret!')
   myidler.run()

**IMAPIdler** will connect to given IMAP mailbox (default folder is ``INBOX``),
process any messages in there and after that it will switch to IDLE and process
any incoming messages.

Processing is done by calling ``self.process_message(message_as_string)``. If
that method returns ``True`` message will be moved from source IMAP folder to
destination (default is ``INBOX.done``).

For debuging purposes you can use standard python logging::

   import logging
   logger = logging.getLogger('imapidler')
   logger.setLevel(logging.DEBUG)

and handle output way you want, like file, stream, etc..

You can also avoid entering IDLE loop with ``runonce()``::

   myidler.runonce()
