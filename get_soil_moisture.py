from ftplib import FTP_TLS
import configparser
from importlib.resources import files
import os
from dataclasses import dataclass

@dataclass
class FTPCredentials:
    host: str
    user: str
    password: str

def get_ftp_credentials(service: str) -> FTPCredentials:
    config = configparser.ConfigParser()
    home_dir = os.path.expanduser('~')
    config.read(os.path.join(home_dir, '.api_credentials.ini'))

    ftp_config = config[service]
    return FTPCredentials(
        host=ftp_config['host'],
        user=ftp_config['user'],
        password=ftp_config['password']
    )

def get_ftp_data(credentials: FTPCredentials, local_file, remote_file):
    """DEPRECATED: does not seem to work"""
    try:
        ftps = FTP_TLS(credentials.host, passwd=credentials.password)
        ftps.set_pasv(True)

        print("Connecting to FTP server...")
        ftps.connect(port=990, timeout=10)
        print(f"Connected to FTP server: {credentials.host}")

        ftps.prot_p()
        files = ftps.nlst()
        print("Files in FTP directory:")
        for filename in files:
            print(f" - {filename}")

        # with open(local_file, 'wb') as f:
        #     ftp.retrbinary(f'RETR {remote_file}', f.write)
        #     print(f"Downloaded {remote_file} to {local_file}")

        ftps.quit()

    except Exception as e:
        print(f"FTP error: {e}")


# Example Usage:
soil_moisture_service = 'SpaceApps_SMOS_NRT'
credentials = get_ftp_credentials(soil_moisture_service)
get_ftp_data(credentials, 'local_soil_moisture_file.dat', 'remote_soil_moisture_file.dat')