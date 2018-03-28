# coding=utf-8

"""Message handling classes and methods for sending, receiving, and processing messages between Processes"""


import PyQt4.QtCore as qc
import multiprocessing as mp


class Message(object):
    """A message object that can contain more than just strings"""
    def __init__(self, target_obj, action, action_settings, recepient_pipe):
        self.target_obj = target_obj
        self.action = action
        self.action_settings = action_settings
        self.recepient_pipe = recepient_pipe


class ProcessMessageHandler(object):
    """Handles sending a message to a separate process and waiting for a response,
    then updating an internal state to reflect the reception of that response"""
    def __init__(self, destination, target_obj, action, action_settings, callable_fn):
        self.destination = destination
        self.target_obj = target_obj
        self.action = action
        self.action_settings = action_settings
        self.callable_fn = callable_fn

    def send(self):
        """Sends a message off to a process, and blocks until it receives a response.
        changes internal msg_rcvd state to True once the response is received"""
        self.self_pipe, self.recepient_pipe = mp.Pipe()
        msg = Message(self.target_obj, self.action, self.action_settings, self.recepient_pipe)
        self.destination.put_nowait(msg)
        qc.QTimer.singleShot(5, self.ready_with_callable)

    def ready_with_callable(self, callable_fn):
        """Send the designated message; if receipt, call the provided callable_fn"""
        self.send()
        if self.ready():
            callable_fn()
        else:
            qc.QTimer.singleShot(5, lambda c=callable_fn: self.send_with_callable(c))

    def ready(self):
        """Checks that the message has been received, and the recepient has sent a notice of receipt"""
        if self.self_pipe.poll():
            # if there is a message in the pipe, it means our message was successfully received
            self.self_pipe.recv()
            self.self_pipe.close()
            self.recepient_pipe.close()
            return True
        else:
            return False
