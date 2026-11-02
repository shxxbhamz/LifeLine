import logging

from .notifications import (
    dispatch_emergency_notification_wave,
)


logger = logging.getLogger(__name__)


class EmergencyObserver:
    """
    Observer interface for emergency broadcast events.
    """

    def update(
        self,
        emergency_request,
        request_matches,
    ):
        raise NotImplementedError(
            "Emergency observers must implement update()."
        )


class DonorNotificationListener(EmergencyObserver):
    """
    Concrete Observer.

    Reacts when the EmergencyBroadcastManager announces
    that a group of matched donors should be notified.
    """

    def update(
        self,
        emergency_request,
        request_matches,
    ):
        if emergency_request is None:
            return {
                "selected": 0,
                "dispatched": 0,
                "skipped": 0,
                "failed": 0,
            }

        if not request_matches:
            return {
                "selected": 0,
                "dispatched": 0,
                "skipped": 0,
                "failed": 0,
            }

        logger.info(
            "DonorNotificationListener received "
            "emergency broadcast event for request %s.",
            emergency_request.id,
        )

        return dispatch_emergency_notification_wave(
            request_matches
        )


class EmergencyBroadcastManager:
    """
    Subject in the Observer pattern.

    Maintains registered observers and notifies them
    when an emergency donor notification wave should
    be broadcast.
    """

    def __init__(self):
        self._observers = []

    def attach(self, observer):
        """
        Register an observer if it is not already attached.
        """

        if observer not in self._observers:
            self._observers.append(
                observer
            )

    def detach(self, observer):
        """
        Remove an observer from the subject.
        """

        if observer in self._observers:
            self._observers.remove(
                observer
            )

    def notify(
        self,
        emergency_request,
        request_matches,
    ):
        """
        Notify every registered observer.

        Returns each observer's result so the caller
        can record/log the outcome.
        """

        results = []

        for observer in self._observers:
            try:
                result = observer.update(
                    emergency_request,
                    request_matches,
                )

                results.append(
                    result
                )

            except Exception:
                logger.exception(
                    "Emergency observer %s failed "
                    "for emergency request %s.",
                    observer.__class__.__name__,
                    (
                        emergency_request.id
                        if emergency_request
                        else None
                    ),
                )

        return results