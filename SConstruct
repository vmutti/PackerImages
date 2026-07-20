vars = Variables(None, ARGUMENTS)
vars.AddVariables(
    ('LOCATION', 'Location running the build'),
    ('STAGE', 'Environment (dev, prod, ...) the build is running in'),
)

env = Environment(
    variables=vars,
    toolpath=['./scons_helpers'],
    tools=['default', 'packer'],
)
Help(vars.GenerateHelpText(env))

env.PackerLayers('layers')
env.PackerGroups('groups')
env.PackerImages('images')
env.PackerLocations('locations')
env.PackerEnvironments('environments')

env.PackerBuildImages()
