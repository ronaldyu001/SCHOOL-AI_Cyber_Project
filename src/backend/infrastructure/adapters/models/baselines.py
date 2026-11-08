"""Read data-only baseline bundles under .models/<task>/ without loading weights."""
import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from domain.entities.datasets.common import CyberTask
from domain.entities.models import ModelBundle

class BaselineUnavailable(LookupError):
    pass

class FileBaselineCatalog:
    def __init__(self, root):
        self.root = Path(root)

    def path(self, task):
        task = CyberTask(task).value
        path = self.root / task / 'baseline.zip'
        if not path.is_file():
            raise BaselineUnavailable('Baseline bundle is not installed for this task')
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError('Baseline bundle must remain inside the configured model directory')
        try:
            with ZipFile(path) as archive:
                member = archive.getinfo('manifest.json')
                if member.file_size > 64 * 1024**2: raise ValueError('Baseline manifest is too large')
                bundle = ModelBundle(archive.read(member).decode('utf-8'))
            if bundle.task.value != task:
                raise ValueError('Baseline manifest does not match task')
        except (BadZipFile, KeyError, UnicodeError) as error:
            raise ValueError('Invalid baseline bundle') from error
        return path

    def list(self):
        descriptions = {'network_intrusion': ('tabm', 'TabM · notebook epoch 26'),
                        'malware_detection': ('malconv', 'MalConv · notebook best checkpoint'),
                        'phishing_detection': ('transformer', 'BART-large-MNLI · zero-shot')}
        result = []
        for task in CyberTask:
            architecture, name = descriptions[task.value]
            item = dict(task=task.value, architecture=architecture, name=name, available=False)
            try:
                self.path(task)
                item['available'] = True
            except (BaselineUnavailable, ValueError, OSError) as error:
                item['reason'] = str(error)
            result.append(item)
        return result
