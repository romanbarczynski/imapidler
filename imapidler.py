# -*- coding: utf-8 -*-
from imapclient import IMAPClient
from logging import getLogger
import time, socket

__author__ = 'romke'
__all__ = ['IMAPIdler']

class IMAPIdler(object):

    Error = Exception
    ServerError = Exception
    FetchingError = Exception

    def __init__(self, host, login, password, port=143,
                 source='INBOX', dest='INBOX.done', idle_timeout=60,
                 processor=None):
        self.server = None
        self.in_idle = False
        self.logger = getLogger('imapidler')
        self.host = host
        self.login = login
        self.password = password
        self.port = port
        self.source = source
        self.dest = dest
        self.idle_timeout = idle_timeout
        if processor:
            self.process_message = processor

    def _connect(self):
        try:
            self.logger.info("Connecting to server %s:%d with user %s",
                              self.host, self.port, self.login)

            self.server = IMAPClient(self.host, port=self.port)
            #, use_uid=True, ssl=False)
            self.server.login(self.login, self.password)
            self.logger.debug("Selecting '%s'...", self.source)
            info = self.server.select_folder(self.source)
            self.logger.debug("Connect info: %s", info)

        except (IMAPClient.Error, socket.error), e:
            self.logger.error("Cannot connect to server %s:%d, reason: %s",
                              self.host, self.port, e)
            self.server = None
            raise IMAPIdler.ServerError()

    def _fetch(self):
        """
        Fetch all mail in currently selected folder & send it to process_message

        After successfull processing message is moved to self.dest folder.
        """
        try:
            messages = self.server.search(['NOT DELETED'])
            if not len(messages):
                return

            self.logger.info("%d messages found, fetching", len(messages))

            response = self.server.fetch(messages, ['RFC822'])
            count = 0
            for msgid, data in response.iteritems():
                if 'RFC822' not in data:
                    continue
                self.logger.debug("Sending message %s to processor", msgid)

                result = self.process_message(data['RFC822'])

                self.logger.debug("Processor returned %s for message %s",
                                  result, msgid)
                if result:
                    count +=1
                    self.server.copy(msgid, self.dest)
                    self.server.delete_messages(msgid)
            self.server.expunge()
            return count

        except IMAPClient.Error, e:
            self.logger.error("Cannot fetch messages: %s", e)
            raise IMAPIdler.FetchingError()

    def _idle(self):
        """
        Enters IMAP server IDLE, sends NOOP every 5 minutes so server
        should not drop connection. If during IDLE new mail arives it
        calls _fetch to process mail in it and after that returns to
        IDLE state.
        """
        self.server.idle()
        self.in_idle = True

        while True:
            try:
                self.logger.debug("Idler loop...")
                idle = self.server.idle_check(timeout=self.idle_timeout)
                if len(idle):
                    # yay! new messages
                    self.server.idle_done()
                    self.in_idle = False
                    self._fetch()
                    self.server.idle()
                    self.in_idle = True
                else:
                    self.server.idle_done()
                    self.in_idle = False
                    # noop to prevent server dropping connections
                    self.server.noop()
                    self.server.idle()
                    self.in_idle = True

            except IMAPClient.Error, e:
                self.logger.error("Error in Idler loop: %s", e)
                time.sleep(10)

    def _close(self):
        """
        Closes server connection. If in IDLE drops IDLE mode.
        """
        self.logger.debug("Closing server connection...")
        if self.in_idle:
            try:
                self.server.idle_done()
            except Exception: pass
        try:
            self.server.close_folder()
        except Exception: pass
        try:
            self.server.logout()
        except Exception: pass

    def run(self):
        """
        Runs fetch and after that enters IDLE mode.
        """
        try:
            while True:
                try:
                    self._connect()
                    self._fetch()
                    self._idle()
                except socket.error, e:
                    # server dropped us, give it some time and try again
                    self.logger.error("%s", e)
                    time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Received interrupt, finishing...")
            self._close()

    def runonce(self):
        """
        Only runs fetch mode, exits after finishing.
        """
        self._connect()
        self._fetch()
        self._close()

    def process_message(self, message):
        raise NotImplementedError
