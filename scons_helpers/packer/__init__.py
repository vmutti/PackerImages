"""SCons tool for building Packer images from layers/groups/images/locations/environments.

Usage (from SConstruct):

    env = Environment(toolpath=['./scons_helpers'], tools=['default', 'packer'])
    env.PackerLayers('layers')
    env.PackerGroups('groups')
    env.PackerImages('images')
    env.PackerLocations('locations')
    env.PackerEnvironments('environments')
    env.PackerBuildImages()

Each of layers/groups/images/locations/environments is a directory tree where every
leaf directory holding a file named `SConscript` registers one definition. The
definition's name is the leaf directory's path relative to the scanned root (e.g.
`layers/distros/debian-initial/SConscript` registers layer `distros/debian-initial`).
Each SConscript imports `env` plus the registration function for its kind
(`PackerLayer`, `PackerGroup`, `PackerImage`, `PackerLocation`, `PackerEnvironment`)
and calls it once with keyword arguments describing the definition.
"""
import json
import os

from SCons.Errors import UserError
from SCons.Script import Builder


class Registry:
    """Named definitions of one kind (layer/group/image/...), with dependency resolution."""

    def __init__(self, kind):
        self.kind = kind
        self._definitions = {}

    def add(self, name, **fields):
        if name in self._definitions:
            raise UserError(f'{self.kind} {name!r} is already defined')
        self._definitions[name] = fields

    def __getitem__(self, name):
        try:
            return self._definitions[name]
        except KeyError:
            raise UserError(f'Unknown {self.kind} {name!r}') from None

    def __contains__(self, name):
        return name in self._definitions

    @staticmethod
    def _deps(definition):
        deps = list(definition.get('uses') or [])
        depends = definition.get('depends')
        if depends:
            deps.append(depends)
        return deps

    def resolve(self, names, _seen=None, _visiting=None):
        """Flatten `names` and their transitive `uses`/`depends` into dependency order."""
        if _seen is None:
            _seen = []
        if _visiting is None:
            _visiting = set()
        for name in names:
            if name in _seen:
                continue
            if name in _visiting:
                raise UserError(f'Cyclic {self.kind} dependency involving {name!r}')
            _visiting.add(name)
            self.resolve(self._deps(self[name]), _seen, _visiting)
            _visiting.discard(name)
            if name not in _seen:
                _seen.append(name)
        return _seen


LAYERS = Registry('layer')
GROUPS = Registry('group')
IMAGES = Registry('image')
LOCATIONS = Registry('location')
ENVIRONMENTS = Registry('environment')


class PackerConfig:
    """Accumulates the pieces of a single Packer HCL2-JSON template as layers/groups/etc apply."""

    def __init__(self, name):
        self.name = name
        self.type = 'null'
        self.variables = {}
        self.locals = {}
        self.builder = {}
        self.provisioners = []
        self.post_processors = []

    def apply(self, *, type=None, variables=None, locals=None, builder=None,
              provisioners=None, post_processors=None, **_ignored):
        if type is not None:
            self.type = type
        self.variables.update(variables or {})
        self.locals.update(locals or {})
        self.builder.update(builder or {})
        self.provisioners += provisioners or []
        self.post_processors += post_processors or []

    def to_dict(self):
        result = {
            'source': {self.type: {self.name: self.builder}},
            'build': {'sources': [f'source.{self.type}.{self.name}']},
        }
        if self.variables:
            result['variable'] = self.variables
        if self.locals:
            result['locals'] = self.locals
        if self.post_processors:
            result['build']['post-processor'] = self.post_processors
        if self.provisioners:
            result['build']['provisioner'] = self.provisioners
        return result


def _write_json(path, data):
    with open(path, 'w') as stream:
        json.dump(data, stream, indent=4)


def _scan(env, registry, root_dir, export_name):
    root_path = env.Dir(root_dir).get_abspath()
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames.sort()
        if 'SConscript' not in filenames:
            continue
        sconscript = os.path.join(dirpath, 'SConscript')
        name = os.path.relpath(dirpath, root_path).replace(os.sep, '/')

        def register(_name=name, _source=sconscript, **fields):
            registry.add(_name, _source=_source, **fields)

        env.SConscript(sconscript, exports={'env': env, export_name: register})


def _packer_layers(env, root_dir):
    _scan(env, LAYERS, root_dir, 'PackerLayer')


def _packer_groups(env, root_dir):
    _scan(env, GROUPS, root_dir, 'PackerGroup')


def _packer_images(env, root_dir):
    _scan(env, IMAGES, root_dir, 'PackerImage')


def _packer_locations(env, root_dir):
    _scan(env, LOCATIONS, root_dir, 'PackerLocation')


def _packer_environments(env, root_dir):
    _scan(env, ENVIRONMENTS, root_dir, 'PackerEnvironment')


def _resolve_image_config(env, image_name):
    image_def = IMAGES[image_name]
    config = PackerConfig(image_name)
    for layer_name in LAYERS.resolve(image_def.get('layers') or []):
        config.apply(**LAYERS[layer_name])
    for group_name in GROUPS.resolve(image_def.get('groups') or []):
        config.apply(**GROUPS[group_name])
    location_def = LOCATIONS[env['LOCATION']]
    config.apply(locals=location_def.get('locals'))
    config.apply(locals=(location_def.get('locals_by_environment') or {}).get(env['STAGE']))
    config.apply(locals=ENVIRONMENTS[env['STAGE']].get('locals'))
    config.apply(**image_def)
    return config


def _image_config_sources(env, image_name):
    image_def = IMAGES[image_name]
    sources = [
        LOCATIONS[env['LOCATION']]['_source'],
        ENVIRONMENTS[env['STAGE']]['_source'],
        image_def['_source'],
    ]
    for layer_name in LAYERS.resolve(image_def.get('layers') or []):
        sources.append(LAYERS[layer_name]['_source'])
    for group_name in GROUPS.resolve(image_def.get('groups') or []):
        sources.append(GROUPS[group_name]['_source'])
    return sources


def _emit_image_config(target, source, env):
    return [env['IMAGE_PACKER_CONFIG_PATH']], _image_config_sources(env, env['IMAGE_NAME'])


def _build_image_config(target, source, env):
    config = _resolve_image_config(env, env['IMAGE_NAME'])
    _write_json(str(target[0]), config.to_dict())


def _emit_image_vars(target, source, env):
    return [env['IMAGE_VARS_PATH']], [LOCATIONS[env['LOCATION']]['_source'], IMAGES[env['IMAGE_NAME']]['_source']]


def _build_image_vars(target, source, env):
    data = {
        'target': env['IMAGE_NAME'],
        'build_directory': env['BUILD_DIR'],
        'stage': env['STAGE'],
        'location': env['LOCATION'],
    }
    depends = IMAGES[env['IMAGE_NAME']].get('depends')
    if depends:
        data['source'] = depends
    _write_json(str(target[0]), data)


def _emit_packer_build(target, source, env):
    source = [env['IMAGE_PACKER_CONFIG_PATH'], env['IMAGE_VARS_PATH']]
    target = [env['IMAGE_PATH_BASE'] + ext for ext in IMAGES[env['IMAGE_NAME']].get('extensions') or []]
    target.append(env['IMAGE_LOG_PATH'])
    return target, source


def _generate_packer_build(target, source, env, for_signature):
    env['ENV']['PACKER_LOG'] = 1
    env['ENV']['PACKER_LOG_PATH'] = str(target[-1])
    return f'packer build -force -var-file {source[1]} {source[0]}'


def _layer_http_dirs(image_name):
    """Absolute paths of `http/` directories among the layers this image resolves, in order."""
    dirs = []
    for layer_name in LAYERS.resolve(IMAGES[image_name].get('layers') or []):
        http_dir = os.path.join(os.path.dirname(LAYERS[layer_name]['_source']), 'http')
        if os.path.isdir(http_dir):
            dirs.append(http_dir)
    return dirs


def _build_one_image(env, image_name):
    image_env = env.Clone()
    image_env['IMAGE_NAME'] = image_name
    image_env['BUILD_DIR'] = env['BUILD_DIR']
    base = f"{env['BUILD_DIR']}/{image_name}"
    image_env['IMAGE_PATH_BASE'] = base
    image_env['IMAGE_VARS_PATH'] = base + '/vars.json'
    image_env['IMAGE_PACKER_CONFIG_PATH'] = base + '/config.pkr.json'
    image_env['IMAGE_LOG_PATH'] = base + '/log'

    config_node = image_env.PackerImageConfig()
    vars_node = image_env.PackerImageVars()
    http_nodes = [
        image_env.Install(base + '/http', os.path.join(http_dir, fname))
        for http_dir in _layer_http_dirs(image_name)
        for fname in sorted(os.listdir(http_dir))
    ]
    build_node = image_env.PackerBuild()
    image_env.Depends(build_node, config_node)
    image_env.Depends(build_node, vars_node)
    image_env.Depends(build_node, http_nodes)
    return build_node


def _packer_build_images(env):
    location_name = env.get('LOCATION')
    stage_name = env.get('STAGE')
    if not location_name or not stage_name:
        raise UserError('LOCATION and STAGE must be set, e.g. scons LOCATION=Thiala STAGE=dev')
    if location_name not in LOCATIONS:
        raise UserError(f'Unknown location {location_name!r}')
    if stage_name not in ENVIRONMENTS:
        raise UserError(f'Unknown environment {stage_name!r}')

    env['LOCATION'] = location_name
    env['STAGE'] = stage_name
    env['BUILD_DIR'] = f'builds/{location_name}/{stage_name}'
    env['ENV']['HOME'] = os.environ['HOME']
    env['ENV']['USER'] = os.environ['USER']
    env['ENV']['LOGNAME'] = os.environ['LOGNAME']
    if 'SSH_AUTH_SOCK' in os.environ:
        env['ENV']['SSH_AUTH_SOCK'] = os.environ['SSH_AUTH_SOCK']

    image_names = IMAGES.resolve(LOCATIONS[location_name].get('images') or [])
    built = {}
    for image_name in image_names:
        built[image_name] = _build_one_image(env, image_name)
        depends = IMAGES[image_name].get('depends')
        if depends:
            env.Depends(built[image_name], built[depends])
    return built


def generate(env):
    env.AddMethod(_packer_layers, 'PackerLayers')
    env.AddMethod(_packer_groups, 'PackerGroups')
    env.AddMethod(_packer_images, 'PackerImages')
    env.AddMethod(_packer_locations, 'PackerLocations')
    env.AddMethod(_packer_environments, 'PackerEnvironments')
    env.AddMethod(_packer_build_images, 'PackerBuildImages')

    env.Append(BUILDERS={
        'PackerImageConfig': Builder(action=_build_image_config, emitter=_emit_image_config),
        'PackerImageVars': Builder(action=_build_image_vars, emitter=_emit_image_vars),
        'PackerBuild': Builder(generator=_generate_packer_build, emitter=_emit_packer_build),
    })


def exists(env):
    return env.Detect('packer')
