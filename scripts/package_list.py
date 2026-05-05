from pathlib import Path

git_root_folder = Path(Path(__file__).parent, '../')

# IMPORTANT: The order of the packages matters because of dependencies
distribution_packages = [
    {
        'name': 'pylab-ml',
        'dir': Path(git_root_folder),
        'namespace': 'pylab_ml'
    },
]

integration_test_packages = [
]
