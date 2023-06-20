import os
from datetime import datetime, date, timedelta
import time
import concurrent.futures
import subprocess
import traceback

import requests

from utils import get_logger, split_file, get_requirements_path, get_common_log_path, get_pip_download_log_path, get_packages_path


yesterday = date.today() - timedelta(days=1)
common_logger = get_logger('common_logger', get_common_log_path(yesterday))
pip_download_logger = get_logger('pip_download_logger', get_pip_download_log_path(yesterday))

def get_package_info(day: date):
    """
    Get package information from the `libraries.io`.
    :param day: The day to get package information.
    """
    try:
        package_metadatas = []
        published_day = day
        page_num = 1
        while published_day >= day:
            common_logger.info(f'Get package information from page {page_num} started.')
            data = get_one_page_package_info(page_num)
            common_logger.info(f'Get package information from page {page_num} finished.')

            package_metadata = data[-1]
            published_day = datetime.strptime(package_metadata['latest_release_published_at'], '%Y-%m-%dT%H:%M:%S.%fZ').date()
            if published_day > day:
                page_num += 1
                time.sleep(1)
            elif published_day == day:
                for package_metadata in data:
                    d = datetime.strptime(package_metadata['latest_release_published_at'], '%Y-%m-%dT%H:%M:%S.%fZ').date()
                    if d == day:
                        package_metadatas.append(package_metadata)
                    else:
                        break
                page_num += 1
                time.sleep(1)
            else:
                for package_metadata in data:
                    d = datetime.strptime(package_metadata['latest_release_published_at'], '%Y-%m-%dT%H:%M:%S.%fZ').date()
                    if d == day:
                        package_metadatas.append(package_metadata)
                    else:
                        break
        common_logger.info(f'Get {len(package_metadatas)} packages information.')
        return package_metadatas
    except Exception as e:
        common_logger.error(e)
        traceback.print_exc()
        return None
    
def get_one_page_package_info(page_num: int, retry_times: int = 3, retry_interval: int = 30):
    """
    Get one page package information from the `libraries.io`.
    :param page_num: The page number to get package information.
    """
    response = requests.get('https://libraries.io/api/search', params={
        'platforms': 'pypi',
        'sort': 'latest_release_published_at',
        'languages': 'python',
        'per_page': 100,
        'page': page_num,
        'api_key': 'd0919d82453d267d023cb0e48e8a3de9'
    })
    if response.status_code != 200:
        # raise Exception('Request failed with status code: {}'.format(response.status_code))
        common_logger.error(f'Request failed with status code: {response.status_code}')
    else:
        retry_times -= 1
        while retry_times > 0:
            time.sleep(retry_interval)
            response = requests.get('https://libraries.io/api/search', params={
                'platforms': 'pypi',
                'sort': 'latest_release_published_at',
                'languages': 'python',
                'per_page': 100,
                'page': page_num,
                'api_key': 'd0919d82453d267d023cb0e48e8a3de9'
            })
            if response.status_code != 200:
                common_logger.error(f'Request failed with status code: {response.status_code}')
                retry_times -= 1
            else:
                break
    return response.json()

def export_package_info(package_info: list, day: date):
    """
    Export package information to the `requirements.txt` file.
    :param package_info: The package information to export.
    """
    with open(get_requirements_path(day), 'w') as f:
        for package_metadata in package_info:
            if package_metadata['latest_release_number']:
                f.write('{}=={}\n'.format(package_metadata['name'], package_metadata['latest_release_number']))
            else:
                f.write('{}\n'.format(package_metadata['name']))

def download_packages(day: date, piece_number: int = 0):
    """
    Download packages from the `PyPI`.
    :param day: The day to download packages.
    :param piece_number: The piece number of the `requirements.txt` file.
    """
    destination_path = get_packages_path(day)
    requirements_file_path = get_requirements_path(day)
    if piece_number > 0:
        requirements_file_path += piece_number
    os.makedirs(get_packages_path(day), exist_ok=True)
    cmd = f'./download.sh {destination_path} {requirements_file_path}'
    pip_download_logger.info(cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate()
    pip_download_logger.info(output.decode())
    pip_download_logger.error(error.decode())

if __name__ == '__main__':
    today = date.today()
    yesterday = today - timedelta(days=1)
    # package_info = get_package_info(yesterday)
    # export_package_info(package_info, yesterday)
    # download_packages(yesterday)
    piece_number = 8
    common_logger.info(f'Split requirements.txt file into {piece_number} pieces.')
    split_file(get_requirements_path(yesterday), piece_number)
    with concurrent.futures.ThreadPoolExecutor(max_workers=piece_number) as executor:
        for i in range(piece_number):
            common_logger.info(f'Download packages from piece {i} started.')
            executor.submit(download_packages, yesterday, i)