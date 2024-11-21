import yaml
import json
import os.path

vars = Variables()
vars.AddVariables(
    ('LOCATION','Location running the build'),
    ('STAGE','Stage where the build is being run'),
    ('REBUILD','Image to rebuild despite missing changes')
)
myenv = Environment(variables=vars)

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
        return json.load(stream)

def write_json(file_path,data):
    with open(file_path,'w') as stream:
        print('writing to',file_path)
        return json.dump(data,stream,indent=4)


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
    vars['stage']=env['STAGE']
    vars['location']=env['LOCATION']
    vars['ssh_public_key']=read_file(vars['ssh_private_key_path']+".pub")
    depends = env['IMAGE_CONFIG'].get('depends','')
    if depends!='':
        vars['source_path']=env['BUILD_DIR']+'/'+depends
    write_json(str(target[0]),vars)
myenv['BUILDERS']['ImageVars']=Builder(action=build_image_vars,emitter=modify_image_var_targets)

def modify_image_packer_config_targets(target,source,env):
    source = [env['LOCATION_PATH']]
    for layer in env['IMAGE_CONFIG']['layers']:
        fname = layer+"/packer.yml"
        if os.path.isfile(fname):
            source.append(fname)
    target = [env['IMAGE_PACKER_CONFIG_PATH']]
    return target,source
class PackerConfig:
    def __init__(self):
        self.builder={}
        self.post_processors=[]
        self.provisioners=[]
    def update(self,src):
        self.builder.update(src.get('builder',{}))
        self.post_processors += src.get('post-processors',[])
        self.provisioners += src.get('provisioners',[])
    def to_dict(self):
        res = {}
        if self.builder!={}:
            res['builders']=[self.builder]
        if self.post_processors!=[]:
            res['post-processors']=self.post_processors
        if self.provisioners!=[]:
            res['provisioners']=self.provisioners
        return res
def build_packer_image_config(target,source,env):
    packer_config = PackerConfig()
    print(str(target[0]),'starting with',packer_config.to_dict())
    for layer_path in source[1:]:
        print(str(target[0]),'using layer',layer_path)
        packer_config.update(read_yaml(str(layer_path)))
    packer_config.update(env['LOCATION_CONFIG'].get('packer',{}))
    packer_config.update(env['IMAGE_CONFIG'].get('packer',{}))
    print(str(target[0]),'ending with',packer_config.to_dict())
    write_json(str(target[0]),packer_config.to_dict())
myenv['BUILDERS']['ImagePackerConfig']=Builder(action=build_packer_image_config,emitter=modify_image_packer_config_targets)


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
    return f'packer build -force -var-file {source[1]} {source[0]}'
myenv['BUILDERS']['Image']=Builder(generator=generate_build_image,emitter=modify_image_targets)


def BuildImage(env,image_config):
    env['IMAGE_CONFIG']=image_config
    env['IMAGE_PATH_BASE']=env['BUILD_DIR']+'/'+image_config['name']
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
    return image
myenv.AddMethod(BuildImage)

def BuildImages(env):
    images={}
    env['BUILD_DIR'] =f'builds/{env["LOCATION"]}/{env["STAGE"]}'
    env['LOCATION_PATH']=f'locations/{env["LOCATION"]}_{env["STAGE"]}.yml'
    env['LOCATION_CONFIG'] = read_yaml(env['LOCATION_PATH'])
    for image_config in env['LOCATION_CONFIG']['images']:
        image_env = env.Clone()
        image = image_env.BuildImage(image_config)
        images[image_config['name']]=image
        if 'depends' in image_config:
            image_env.Depends(image,images[image_config['depends']])

myenv['ENV']['VAGRANT_WSL_ENABLE_WINDOWS_ACCESS']="1"
myenv['ENV']['PATH']+=":/mnt/c/WINDOWS/system32/:/mnt/c/WINDOWS/System32/WindowsPowershell/v1.0/"
myenv.AddMethod(BuildImages)
myenv.BuildImages()

# rebuild = GetOption('rebuild')
# if rebuild !='':
#     AlwaysBuild(Page(rebuild))
