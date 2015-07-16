from octane import handlers


urls = (
    r'/clusters/(?P<cluster_id>\d+)/upgrade/clone/?$',
    handlers.ClusterCloneHandler,
    r'/clusters/(?P<cluster_id>\d+)/upgrade/assign/?$',
    handlers.UpgradeNodeAssignmentHandler,
)
