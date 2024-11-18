import yaml
import json
import os.path

vars = Variables()
vars.AddVariables(
    ('LOCATION','Location running the build'),
    ('STAGE','Stage where the build is being run'),
    ('REBUILD','Image to rebuild despite missing changes')
)
env = Environment(variables=vars)

def read_file(file_path):
    with open(file_path) as stream:
        return stream.read()

def read_yaml(file_path,default={}):
    with open(file_path) as stream:
        result = yaml.safe_load(stream)
        if result:
            return result
        else:
            return default
def read_json(file_path):
    with open(file_path) as stream:
        return json.safe_load(stream)

def write_json(file_path,data):
    with open(file_path,'w') as stream:
        return json.dump(data,stream)


def modify_image_var_targets(target,source,env):
    source = [env['LOCATION_PATH']]
    for layer in env['IMAGE_CONFIG']['layers']:
        fname = layer+"/vars.yml"
        if os.path.isfile(fname):
            source.append(fname)
    target = [env['IMAGE_VARS_PATH']]
    return target,source
def build_image_vars(target,source,env):
    vars = dict()
    for layer_path in source[1:]:
        vars.update(read_yaml(str(layer_path)))
    vars.update(env['LOCATION_CONFIG'].get('vars',{}))
    vars.update(env['IMAGE_CONFIG'].get('vars',{}))
    vars['target']=env['IMAGE_PATH']
    vars['http_path']=env['IMAGE_HTTP_PATH']
    vars['ssh_public_key']=read_file(vars['ssh_private_key_path']+".pub")
    write_json(str(target[0]),vars)
env['BUILDERS']['ImageVars']=Builder(action=build_image_vars,emitter=modify_image_var_targets)

def modify_image_packer_config_targets(target,source,env):
    source = [env['LOCATION_PATH']]
    for layer in env['IMAGE_CONFIG']['layers']:
        fname = layer+"/packer.yml"
        if os.path.isfile(fname):
            source.append(fname)
    target = [env['IMAGE_PACKER_CONFIG_PATH']]
    return target,source
class PackerConfig:
    builder={}
    post_processors=[]
    def update(self,src):
        self.builder.update(src.get('builder',{}))
        self.post_processors += src.get('post-processors',[])
    def to_dict(self):
        return {
            'builders':[self.builder],
            'post-processors':[self.post_processors]
        }
def build_packer_image_config(target,source,env):
    packer_config = PackerConfig()
    for layer_path in source[1:]:
        packer_config.update(read_yaml(str(layer_path)))
    packer_config.update(env['LOCATION_CONFIG'].get('packer',{}))
    packer_config.update(env['IMAGE_CONFIG'].get('packer',{}))
    write_json(str(target[0]),packer_config.to_dict())
env['BUILDERS']['ImagePackerConfig']=Builder(action=build_packer_image_config,emitter=modify_image_packer_config_targets)


def modify_image_targets(target,source,env):
    source = [env['IMAGE_PACKER_CONFIG_PATH'],env['IMAGE_VARS_PATH']]
    target = [env['IMAGE_PATH'],env['IMAGE_LOG_PATH']]
    return target,source
def generate_build_image(target,source,env,for_signature):
    env['ENV']['PACKER_LOG']=1
    env['ENV']['PACKER_LOG_PATH']=target[1]
    return f'packer build -force -var-file {source[1]} {source[0]}'
env['BUILDERS']['Image']=Builder(generator=generate_build_image,emitter=modify_image_targets)


def BuildImage(env,image_config):
    env['IMAGE_CONFIG']=image_config
    env['IMAGE_PATH']=env['BUILD_DIR']+'/'+image_config['name']
    env['IMAGE_VARS_PATH']=env['BUILD_DIR']+'/'+image_config['name']+".packer_vars.json"
    env['IMAGE_HTTP_PATH']=env['BUILD_DIR']+'/'+image_config['name']+".http"
    env['IMAGE_PACKER_CONFIG_PATH']=env['BUILD_DIR']+'/'+image_config['name']+".packer_config.json"
    env['IMAGE_LOG_PATH']=env['BUILD_DIR']+'/'+image_config['name']+".log"
    
    config = env.ImagePackerConfig(image_config['name'])
    vars = env.ImageVars(image_config['name'])
    image = env.Image(image_config['name'])
    env.Depends(image,config)
    env.Depends(image,vars)
    for layer in env['IMAGE_CONFIG']['layers']:
        dname = layer+"/http"
        if os.path.isdir(dname):
            http = env.Install(target=env['IMAGE_HTTP_PATH'],source=Glob(dname+'/*'))
            env.Depends(image,http)
    return vars
env.AddMethod(BuildImage)

def BuildImages(env):
    images={}
    env['BUILD_DIR'] =f'builds/{env["LOCATION"]}/{env["STAGE"]}'
    env['LOCATION_PATH']=f'locations/{env["LOCATION"]}.yml'
    env['LOCATION_CONFIG'] = read_yaml(env['LOCATION_PATH'])
    for image_config in env['LOCATION_CONFIG']['images']:
        image = env.BuildImage(image_config)
        images[image_config['name']]=image
        if 'depends' in image_config:
            Depends(image,images[image_config['depends']])
env.AddMethod(BuildImages)
env.BuildImages()

# rebuild = GetOption('rebuild')
# if rebuild !='':
#     AlwaysBuild(Page(rebuild))
