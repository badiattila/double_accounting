import os, sys, importlib, django

print("CWD:", os.getcwd())
print("Python:", sys.executable)
print("DJANGO_SETTINGS_MODULE:", os.environ.get("DJANGO_SETTINGS_MODULE"))
try:
    import ledger_proj.settings as s

    print("Loaded settings OK.")
    from django.conf import settings

    django.setup()
    print("INSTALLED_APPS:")
    for a in settings.INSTALLED_APPS:
        print("  -", a)
    try:
        import accounting

        print("Imported 'accounting' OK:", accounting.__file__)
    except Exception as e:
        print("Import accounting FAILED:", e)
except Exception as e:
    print("Settings load FAILED:", e)
