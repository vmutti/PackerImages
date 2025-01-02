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

def get_layers(layers,found=set([])):
    result = []
    for layer in layers:
        if layer not in found:

            fname = f'layers/{layer}/packer.yml'
            # print(f'parsing {layer}')
            if os.path.isfile(fname):
                layer_config = read_yaml(fname)
                sub_layers=layer_config.get('layers',[])
                # print(f'got sublayers {sub_layers}')
                if len(sub_layers)>0:
                    new_layers=get_layers(sub_layers,found|set(result+[layer]))
                    result += new_layers
                    for sub_layer in new_layers:
                        dname=f'layers/{sub_layer}/'
                        if not os.path.isdir(dname):
                            raise ValueError(f'Layer {sub_layer} included from {layer} does not exist')
            result.append(layer)
    return result


def modify_image_var_targets(target,source,env):
    source = [env['LOCATION_PATH']]
    target = [env['IMAGE_VARS_PATH']]
    return target,source
def build_image_vars(target,source,env):
    vars = {
        'target': env['IMAGE_NAME'],
        'build_directory': env['BUILD_DIR'],
        'stage': env['STAGE'],
        'location': env['LOCATION'],
    }
    if 'depends' in env['IMAGE_CONFIG']:
        vars['source']=env['IMAGE_CONFIG']['depends']
    write_json(str(target[0]),vars)
myenv['BUILDERS']['ImagePackerVars']=Builder(
    action=build_image_vars,
    emitter=modify_image_var_targets
)

def modify_image_packer_config_targets(target,source,env):
    source = [env['LOCATION_PATH']]
    for layer in get_layers(env['IMAGE_CONFIG']['layers']):
        fname = f'layers/{layer}/packer.yml'
        if os.path.isfile(fname):
            source.append(fname)
    target = [env['IMAGE_PACKER_CONFIG_PATH']]
    return target,source
class PackerConfig:
    def __init__(self,image_name):
        self.image_name=image_name
        self.type='null'
        self.variables={}
        self.locals={}
        self.local={}
        self.builder={}
        self.provisioners=[]
        self.post_processors=[]
    def update(self,src):
        self.type=src.get('type',self.type)
        self.variables.update(src.get('variables',{}))
        self.locals.update(src.get('locals',{}))
        self.local.update(src.get('local',{}))
        self.builder.update(src.get('builder',{}))
        self.provisioners += src.get('provisioners',[])
        self.post_processors += src.get('post-processors',[])

    def to_dict(self):
        res = {
            'source': {},
            'build': {}
        }
        res['source'][self.type]={}
        res['source'][self.type][self.image_name]=self.builder
        res['build']['sources']=[f'source.{self.type}.{self.image_name}']

        if self.variables!={}:
            res['variable']=self.variables
        if self.locals!={}:
            res['locals']=self.locals
        if self.local!={}:
            res['local']=self.local
        if self.post_processors!=[]:
            res['build']['post-processor']=self.post_processors
        if self.provisioners!=[]:
            res['build']['provisioner']=self.provisioners
        return res

def get_groups(group_configs,groups,found=set([])):
    result = []
    for group in groups:
        if group not in found:
            if group in group_configs:
                group_config = group_configs[group]
                sub_groups=group_config.get('groups',[])
                if len(sub_groups)>0:
                    new_groups=get_groups(group_configs,sub_groups,found|set(result+[group]))
                    result += new_groups
                    for sub_group in new_groups:
                        if subgroup not in group_configs:
                            raise ValueError(f'Group {sub_group} included from {group} does not exist')
            result.append(group)
    return result

def build_packer_image_config(target,source,env):
    packer_config = PackerConfig(env['IMAGE_NAME'])
    for layer_path in source[1:]:
        packer_config.update(read_yaml(str(layer_path)))
    packer_config.update(env['LOCATION_CONFIG'])
    group_configs = env['LOCATION_CONFIG'].get('groups',{})
    image_groups = env['IMAGE_CONFIG'].get('groups',[])
    image_groups = get_groups(group_configs,image_groups)
    for image_group in image_groups:
        packer_config.update(group_configs[image_group])
    packer_config.update(env['IMAGE_CONFIG'])
    write_json(str(target[0]),packer_config.to_dict())
myenv['BUILDERS']['ImagePackerConfig']=Builder(
    action=build_packer_image_config,
    emitter=modify_image_packer_config_targets
)


def modify_image_targets(target,source,env):
    source = [env['IMAGE_PACKER_CONFIG_PATH'],env['IMAGE_VARS_PATH']]
    target = []
    for ext in env['IMAGE_CONFIG'].get('extensions',[]):
        target.append(env['IMAGE_PATH_BASE']+ext)
    target.append(env['IMAGE_LOG_PATH'])
    return target,source
def generate_build_image(target,source,env,for_signature):
    env['ENV']['PACKER_LOG']=1
    env['ENV']['PACKER_LOG_PATH']=target[-1]
    return f'packer build -force -var-file {source[1]} {source[0]}'
myenv['BUILDERS']['Image']=Builder(
    generator=generate_build_image,
    emitter=modify_image_targets
)

def BuildImage(env,image_name,image_config):
    env['IMAGE_NAME']=image_name
    env['IMAGE_CONFIG']=image_config
    env['IMAGE_PATH_BASE']=env['BUILD_DIR']+'/'+image_name
    env['IMAGE_VARS_PATH']=env['IMAGE_PATH_BASE']+"/vars.json"
    env['IMAGE_PACKER_CONFIG_PATH']=env['IMAGE_PATH_BASE']+"/config.pkr.json"
    env['IMAGE_LOG_PATH']=env['IMAGE_PATH_BASE']+"/log"
    env['IMAGE_LAYERS']=get_layers(image_config.get('layers',[]))
    image_packer_config = env.ImagePackerConfig()
    image_packer_vars = env.ImagePackerVars()
    image_packer = env.Image()
    env.Depends(image_packer,image_packer_config)
    env.Depends(image_packer,image_packer_vars)
    return image_packer
myenv.AddMethod(BuildImage)



def BuildImages(env):
    images={}
    env['BUILD_DIR'] =f'builds/{env["LOCATION"]}/{env["STAGE"]}'
    env['LOCATION_PATH']=f'locations/{env["LOCATION"]}/{env["STAGE"]}/builds.yml'
    env['LOCATION_CONFIG'] = read_yaml(env['LOCATION_PATH'])
    image_names = []
    image_configs = env['LOCATION_CONFIG']['images']
    for image_name in image_configs.keys():
        if image_name not in image_names:
            image_name_stack=[image_name]
            curr_image_name = image_name
            while 'depends' in image_configs[curr_image_name]:
                next_image_name=image_configs[curr_image_name]['depends']
                if next_image_name in image_names+image_name_stack:
                    break
                curr_image_name=next_image_name
                image_name_stack.append(curr_image_name)
            image_names+=image_name_stack[::-1]

    for image_name in image_names:
        image_config = image_configs[image_name]
        image_env = env.Clone()
        image = image_env.BuildImage(image_name,image_config)
        images[image_name]=image
        if 'depends' in image_config:
            image_env.Depends(image,images[image_config['depends']])

# myenv['ENV']['VAGRANT_WSL_ENABLE_WINDOWS_ACCESS']="1"
# myenv['ENV']['PATH']+=":/mnt/c/WINDOWS/system32/"
# myenv['ENV']['PATH']+=":/mnt/c/WINDOWS/System32/WindowsPowershell/v1.0/"
myenv.AddMethod(BuildImages)

myenv.BuildImages()

# rebuild = GetOption('rebuild')
# if rebuild !='':
#     AlwaysBuild(Page(rebuild))
