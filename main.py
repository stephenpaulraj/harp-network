import netifaces
import logging
import subprocess
import time


class HarpNetwork:
    def __init__(self):
        self.setup_logging()

    def setup_logging(self):
        self.logger = logging.getLogger('harp_network_logger')
        self.logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler('harp-network.log')
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_available_interfaces(self):
        return netifaces.interfaces()

    def check_interface_up(self, interface):
        if interface not in ['eth0', 'ppp0', 'eth1', 'usb0']:
            return False
        return netifaces.AF_INET in netifaces.ifaddresses(interface)

    def get_default_interface(self):
        gateways = netifaces.gateways()
        return gateways['default'][netifaces.AF_INET][1] if netifaces.AF_INET in gateways['default'] else None

    def check_internet_connection(self, interface):
        if interface == 'eth1':
            try:
                subprocess.run(['ping', '-c', '1', '192.168.3.1'], check=True, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                self.logger.info("Internet connectivity check passed on interface '%s'", interface)
                return True
            except subprocess.CalledProcessError:
                self.logger.warning("Internet connectivity check failed on interface '%s'", interface)
                return False
        else:
            try:
                subprocess.run(['ping', '-c', '1', '-I', interface, '8.8.8.8'], check=True, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                self.logger.info("Internet connectivity check passed on interface '%s'", interface)
                return True
            except subprocess.CalledProcessError:
                self.logger.warning("Internet connectivity check failed on interface '%s'", interface)
                return False

    def set_default_interface(self, interface):
        try:
            subprocess.run(['sudo', 'ip', 'route', 'replace', 'default', 'dev', interface], check=True)
            self.logger.info("Setting interface '%s' as the default interface.", interface)
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to set default interface: %s", e)

    def bring_up_ppp0(self):
        try:
            subprocess.run(['sudo', 'pon', 'rnet'], check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to bring up ppp0: %s", e)

    def run_service(self):
        while True:
            self.logger.info("Checking interfaces...")
            interfaces = self.get_available_interfaces()
            usb0_found = False
            default_interface = self.get_default_interface()
            internet_interface = None
            eth1_status = None

            for interface in interfaces:
                if self.check_interface_up(interface):
                    self.logger.info("Interface '%s' is up and active.", interface)
                    if interface == 'usb0':
                        usb0_found = True
                    elif interface == 'eth1':
                        eth1_status = "Connected" if self.check_internet_connection(interface) else "Disconnected"
                    elif interface in ['eth0', 'ppp0'] and not usb0_found:
                        if self.check_internet_connection(interface):
                            self.set_default_interface(interface)
                            internet_interface = interface
                            break

            self.logger.info("Default Interface: %s", default_interface)
            self.logger.info("Interface with Internet: %s", internet_interface)
            self.logger.info("Status of eth1: %s", eth1_status)

            if usb0_found:
                self.logger.info("usb0 found, bringing up ppp0...")
                self.bring_up_ppp0()

            time.sleep(5)


if __name__ == "__main__":
    harp_network = HarpNetwork()
    harp_network.run_service()
