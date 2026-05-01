import environ
import os

env = environ.Env(
    
    DEBUG=(bool, False)
)


BASE_DIR = Path(__file__).resolve().parent.parent


environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')


DATABASES = {
    'default': env.db(),
}