from logging import Logger, getLogger

from amplitude import Amplitude, BaseEvent, Config, Identify, EventOptions
from destination_amplitude.utils import callback_function

logger = getLogger("airbyte")

class EventType(Exception):
    pass

class IdentifyEvent(Exception):
    pass

class AmplitudeClient:
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.flush_queue_size = config["flush_queue_size"]
        self.flush_interval_millis = config["flush_interval_millis"]
        self.flush_max_retries = config["flush_max_retries"]
        self.use_batch = config["use_batch"]
        self.is_batch_identify = config["is_batch_identify"]
        self.to_upload_list = []
        self.amplitude_client = Amplitude(
            api_key=self.api_key, configuration=self._get_config()
        )

    def _get_config(self):
        return Config(
            flush_queue_size=self.flush_queue_size,
            flush_interval_millis=self.flush_interval_millis,
            flush_max_retries=self.flush_max_retries,
            use_batch=self.use_batch,
            logger=logger,
            callback=callback_function,
        )

    def create_event(self, event_raw):
        try:
            if not self.is_batch_identify:
                # Create a BaseEvent instance
                if "event_type" not in event_raw.keys():
                    raise EventType(
                        "event_type must be specified in: \n{}".format(event_raw)
                    )
                event = BaseEvent(event_type=event_raw["event_type"])

                for key in event_raw.keys():
                    if key in event.__dict__:
                        event[key] = event_raw[key]
                        {}.pop
                    else:
                        logger.debug("Unexpected property: {}".format(key))
                
                return event
            else:
                # Process user properties
                user_properties = Identify()
                if event_raw["user_properties"]:
                    for k, v in event_raw["user_properties"].items():
                        user_properties.set(k, v)

                    return (
                        user_properties,
                        EventOptions(user_id=event_raw["user_id"]),
                        event_raw["groups"]
                    )
                else:
                    raise IdentifyEvent(
                        "Unexpected property: \n{}".format(event_raw)
                    )

        except EventType:
            raise
        except IdentifyEvent:
            raise
        except Exception as err:
            logger.error(err)
            raise
        finally:
            self.amplitude_client.flush()
    

    
        
    def send(self, list_events):
        if len(list_events) > 0:
            for e in list_events:
                self.amplitude_client.track(e) if not self.is_batch_identify else self.amplitude_client.identify(e[0], e[1], e[2])
        
        self.amplitude_client.shutdown()