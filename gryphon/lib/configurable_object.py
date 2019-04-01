"""
Several objects in the gryphon-framework use the pattern of initializing their
properties from a dictionary, in which the properties are unpredictable and may not be
present from a dictionary, in which the properties are unpredictable and may not be
present.
"""

class ConfigurableObject(object):
    def configure(self, configuration):
        """
        This function is called to configure the object. It should be a series of calls
        to self.init_configurable(configuration).
        """
        raise NotImplementedError

    def init_configurable(self, configurable_name, configuration):
        """
        Helper function to initialize a single configurable property on the object
        if we find a value set for it in the configuration. If we don't find an
        entry for a configurable name, or find a None value, we don't don't do anything
        (which should mean we stick to the default if you've written the class
        properly).
        """
        if hasattr(self, configurable_name) is not True:
            raise Exception(
                'Configuration error: %s has no attribute %s' % (
                self.__class__.__name__,
                configurable_name,
            ))

        if (configurable_name in configuration
                and configuration[configurable_name] is not None):
            setattr(
                self,
                configurable_name,
                configuration[configurable_name],
            )
