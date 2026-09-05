from dify_plugin import DifyPluginEnv, Plugin

# A long video can take ~170 s end to end; the client polls inside that window.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=240))


if __name__ == "__main__":
    plugin.run()
