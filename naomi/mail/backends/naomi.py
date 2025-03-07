import datetime
import os
import webbrowser

from django.conf import settings
from django.core.mail.backends.filebased import EmailBackend
from django.template.loader import render_to_string

import six
import logging


class NaomiBackend(EmailBackend):
    """Email backend for Django that let you preview email on your web browser."""

    def __init__(self, *args, **kwargs):  # noqa: D107
        super().__init__(*args, **kwargs)

    def write_message(self, message):
        attachments = []
        if hasattr(message, "attachments") and message.attachments:
            temporary_path = settings.EMAIL_FILE_PATH
            for attachment in message.attachments:
                if isinstance(attachment, tuple):
                    new_file = open(os.path.join(temporary_path, attachment[0]), "wb+")  # noqa: SIM115
                    if isinstance(attachment[1], str):
                        new_file.write(attachment[1].encode("utf-8"))
                    else:
                        new_file.write(attachment[1])
                    attachments.append([attachment[0], new_file.name])
                    new_file.close()
                else:
                    new_file = open(os.path.join(temporary_path, attachment.name), "wb+")  # noqa: SIM115
                    new_file.write(attachment.read())
                    attachments.append([attachment.name, new_file.name])
                    new_file.close()
        body = message.alternatives[0][0] if hasattr(message, "alternatives") and message.alternatives else message.body
        context = {"message": message, "body": body, "attachments": attachments}
        template_content = render_to_string("naomi/message.html", context)
        if six.PY3:
            self.stream.write(bytes(template_content, "UTF-8"))
        else:
            self.stream.write(template_content.encode("UTF-8"))

    def _get_filename(self):
        """Return a unique file name."""
        if self._fname is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            fname = f"{timestamp}-{abs(id(self))}.html"
            self._fname = os.path.join(self.file_path, fname)
        return self._fname

    def close(self):
        result = super().close()
        webbrowser.open("file://" + self._fname)
        return result

    def send_messages(self, email_messages):
        """Write all messages to the stream in a thread-safe way."""
        if not email_messages:
            return
        with self._lock:
            try:
                stream_created = self.open()
                for message in email_messages:
                    if six.PY3:
                        self.write_message(message)
                    else:
                        self.write_message(message)
                    self.stream.flush()
                if stream_created:
                    self.close()
            except Exception:
                if not self.fail_silently:
                    raise
        return len(email_messages)
