from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "distribucion.settings")
import django
django.setup()

from usuarios.models import crear_grupos_fijos

crear_grupos_fijos()
