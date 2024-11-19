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
        print('writing to',file_path)
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
    vars['target']=env['IMAGE_CONFIG']['name']
    vars['build_dir']=env['BUILD_DIR']
    vars['http_path']=env['IMAGE_HTTP_PATH']
    vars['ssh_public_key']=read_file(vars['ssh_private_key_path']+".pub")
    depends = env['IMAGE_CONFIG'].get('depends','')
    if depends!='':
        vars['source_path']=env['BUILD_DIR']+'/'+depends
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
    provisioners=[]
    def update(self,src):
        self.builder.update(src.get('builder',{}))
        self.post_processors += src.get('post-processors',[])
        self.provisioners += src.get('provisioners',[])
    def to_dict(self):
        res = {}
        if self.builder!={}:
            res['builders']=[self.builder]
        if self.post_processors!=[]:
            res['post-processors']=[self.post_processors]
        if self.provisioners!=[]:
            res['provisioners']=[self.provisioners]
        return res
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
    target = []
    for ext in env['IMAGE_CONFIG'].get('extensions',[]):
        target.append(env['IMAGE_PATH_BASE']+"."+ext)
    target.append(env['IMAGE_LOG_PATH'])
    return target,source
def generate_build_image(target,source,env,for_signature):
    env['ENV']['PACKER_LOG']=1
    env['ENV']['PACKER_LOG_PATH']=target[-1]
    env['ENV']['VAGRANT_WSL_ENABLE_WINDOWS_ACCESS']="1"
    env['ENV']['PATH']+=":/mnt/c/WINDOWS/system32/:/mnt/c/WINDOWS/System32/WindowsPowershell/v1.0/"
    return f'packer build -force -var-file {source[1]} {source[0]}'
env['BUILDERS']['Image']=Builder(generator=generate_build_image,emitter=modify_image_targets)


def BuildImage(env,image_config):
    image_env = env.Clone()
    image_env['IMAGE_CONFIG']=image_config
    image_env['IMAGE_PATH_BASE']=image_env['BUILD_DIR']+'/'+image_config['name']
    image_env['IMAGE_VARS_PATH']=image_env['BUILD_DIR']+'/'+image_config['name']+".packer_vars.json"
    image_env['IMAGE_HTTP_PATH']=image_env['BUILD_DIR']+'/'+image_config['name']+".http"
    image_env['IMAGE_PACKER_CONFIG_PATH']=image_env['BUILD_DIR']+'/'+image_config['name']+".packer_config.json"
    image_env['IMAGE_LOG_PATH']=image_env['BUILD_DIR']+'/'+image_config['name']+".log"
    
    config = image_env.ImagePackerConfig(image_config['name'])
    vars = image_env.ImageVars(image_config['name'])
    image = image_env.Image(image_config['name'])
    image_env.Depends(image,config)
    image_env.Depends(image,vars)
    for layer in image_env['IMAGE_CONFIG']['layers']:
        dname = layer+"/http"
        if os.path.isdir(dname):
            http = image_env.Install(target=image_env['IMAGE_HTTP_PATH'],source=Glob(dname+'/*'))
            image_env.Depends(image,http)
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
