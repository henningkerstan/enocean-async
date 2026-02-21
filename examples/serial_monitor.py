import asyncio
import logging
import signal
import sys

from enocean_async import EEPID, EnOceanGateway, EnOceanUniqueRadioID
from enocean_async.capabilities.state_change import StateChange, StateChangeSource
from enocean_async.eep.message import EEPMessage


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG:    "\033[96;1m",   # bright cyan
        logging.INFO:     "\033[95;1m",   # bright magenta
        logging.WARNING:  "\033[93;1m",   # bright yellow
        logging.ERROR:    "\033[91;1m",   # bright red
        logging.CRITICAL: "\033[97;1;41m",  # bright white on red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"
    
CROSSMARK = "\033[91m✗\033[0m"
EXCLAMATIONMARK = "\033[93m!\033[0m"
TIMERMARK = "\033[94m⏱\033[0m"
RECEIVEMARK = "\033[96m📡\033[0m"
SENDMARK = "\033[94m📤\033[0m"
TELEGRAMMARK = "\033[92m🧾\033[0m"
MESSAGEMARK = "\033[92m✉️\033[0m"
STATECHANGEMARK = "\033[92m🔔\033[0m"
         

async def main(port: str) -> None:
    # set up main loop with exit handler
    loop = asyncio.get_running_loop() 
    stop_event = asyncio.Event() 
    loop.add_signal_handler(signal.SIGINT, stop_event.set) 
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)

    # set up logging
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter( "%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S" ))
    logging.basicConfig(
        level=logging.WARNING,
        handlers=[handler]
)

    print(f"Setting up EnOcean Gateway for module on {port}...")
    gateway = EnOceanGateway(port)

    # callback registration
    gateway.add_esp3_received_callback(lambda pkt: print(f"\n{RECEIVEMARK} Received {pkt}"))
    gateway.add_erp1_received_callback(lambda erp1: print(f"├─ {TELEGRAMMARK} {erp1}"))
    gateway.add_new_device_callback(lambda addr: print(f"├─ {EXCLAMATIONMARK} new device: {addr}"))

    def on_state_change(state_change: StateChange) -> None:
        """Handle state changes emitted by device capabilities."""
        if state_change.source == StateChangeSource.TIMER:
            print(f"\n{TIMERMARK} {STATECHANGEMARK} {state_change}")
        else:
            print(f"╰─ {STATECHANGEMARK} {state_change}")


    gateway.add_state_change_callback(on_state_change)
    gateway.add_eep_message_received_callback(lambda msg: print(f"├─ {MESSAGEMARK} {msg}"))
    gateway.add_ute_received_callback(lambda ute: print(f"╰─ {MESSAGEMARK} successfully parsed to UTE message: {ute}"))
    gateway.add_response_callback(lambda resp: print(f"╰─ {MESSAGEMARK} {resp}"))
    gateway.add_parsing_failed_callback(lambda msg: print(f"╰─ {CROSSMARK} Further parsing failed: {msg}"))
    gateway.add_esp3_send_callback(lambda pkt: print(f"{SENDMARK} Sending {pkt}"))


    print("Starting gateway...")
    await gateway.start()
    print("EnOcean module is ready!")

    # print module info
    print(f"EURID: {await gateway.eurid}")
    print(
        f"Base ID: {await gateway.base_id} (remaining write cycles: {await gateway.base_id_remaining_write_cycles})"
    )
    version_info = await gateway.version_info

    print(f"App description: {version_info.app_description}")
    print(f"App version: {version_info.app_version.version_string}")
    print(f"API version: {version_info.api_version.version_string}")
    print(f"Device version: {version_info.device_version}")

    # add some devices - adopt to your own devices and EEPs
    gateway.add_device(EnOceanUniqueRadioID.from_string("00:00:00:01"), EEPID.from_string("F6-02-01"))
    gateway.add_device(EnOceanUniqueRadioID.from_string("00:00:00:02"), EEPID.from_string("F6-02-01"))


    try:
        from devices import DEVICE_EEP_MAP
        print("Registering devices from device EEP map...")
        for device_id, eep_id in DEVICE_EEP_MAP:
            gateway.add_device(device_id, eep_id)
    except ImportError:
        print("No 'devices.py' file found, skipping device registration.")
    

    # start learning mode
    gateway.start_learning(timeout_seconds=5)

    # Keep the event loop running until CTRL+C is pressed
    print("Running... Press Ctrl+C to exit.") 
    await stop_event.wait() 
    print("Shutting down...")
    gateway.stop()


if __name__ == "__main__":
    first_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if first_arg is None:
        print("Usage: python serial_monitor <serial_port>")
        print("Example: python serial_monitor /dev/tty.usbserial-XYZ")
        sys.exit(1)

    asyncio.run(main(first_arg))
   