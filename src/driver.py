#!/usr/bin/python
# -*- coding: utf-8 -*-

from cloudshell.cli.service.cli import CLI
from cloudshell.cli.service.session_pool_manager import SessionPoolManager
from cloudshell.networking.juniper.cli.juniper_cli_configurator import JuniperCliConfigurator
from cloudshell.networking.juniper.flows.autoload_flow import JunOSAutoloadFlow
from cloudshell.networking.juniper.flows.configuration_flow import JuniperConfigurationFlow
from cloudshell.networking.juniper.flows.connectivity_flow import JuniperConnectivity
from cloudshell.networking.juniper.flows.juniper_enable_disable_snmp_flow import JuniperEnableDisableSnmpFlow
from cloudshell.networking.juniper.flows.juniper_firmware_flow import JuniperFirmwareFlow
from cloudshell.networking.juniper.flows.juniper_state_flow import JuniperStateFlow
from cloudshell.shell.core.driver_utils import GlobalLock
from cloudshell.shell.core.orchestration_save_restore import OrchestrationSaveRestore
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext
from cloudshell.shell.flows.command.basic_flow import RunCommandFlow
from cloudshell.shell.standards.networking.autoload_model import NetworkingResourceModel
from cloudshell.shell.standards.networking.driver_interface import NetworkingResourceDriverInterface
from cloudshell.shell.standards.networking.resource_config import NetworkingResourceConfig
from cloudshell.snmp.snmp_configurator import EnableDisableSnmpConfigurator


class JuniperJunOSShellDriver(ResourceDriverInterface, NetworkingResourceDriverInterface):
    SUPPORTED_OS = [r'[Jj]uniper']
    SHELL_NAME = "Juniper JunOS Router 2G"

    def __init__(self):
        self._cli = None

    def initialize(self, context):
        """Initialize method

        :type context: cloudshell.shell.core.context.driver_context.InitCommandContext
        """

        resource_config = NetworkingResourceConfig.from_context(self.SHELL_NAME, context)
        session_pool_size = int(resource_config.sessions_concurrency_limit)
        self._cli = CLI(SessionPoolManager(max_pool_size=session_pool_size, pool_timeout=100))
        return 'Finished initializing'

    @GlobalLock.lock
    def get_inventory(self, context):
        """Return device structure with all standard attributes

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: response
        :rtype: str
        """

        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(self.SHELL_NAME, context, api, self.SUPPORTED_OS)

            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)
            enable_disable_snmp_flow = JuniperEnableDisableSnmpFlow(cli_configurator, logger)
            snmp_configurator = EnableDisableSnmpConfigurator(enable_disable_snmp_flow, resource_config, logger)

            resource_model = NetworkingResourceModel.from_resource_config(resource_config)

            autoload_operations = JunOSAutoloadFlow(snmp_configurator, logger)
            logger.info('Autoload started')
            response = autoload_operations.discover(self.SUPPORTED_OS, resource_model)
            logger.info('Autoload completed')
            return response

    def run_custom_command(self, context, custom_command):
        """Send custom command

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: result
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)

            send_command_operations = RunCommandFlow(logger, cli_configurator)
            response = send_command_operations.run_custom_command(custom_command)
            return response

    def run_custom_config_command(self, context, custom_command):
        """Send custom command in configuration mode

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: result
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)

            send_command_operations = RunCommandFlow(logger, cli_configurator)
            result_str = send_command_operations.run_custom_config_command(custom_command)
            return result_str

    def ApplyConnectivityChanges(self, context, request):
        """
        Create vlan and add or remove it to/from network interface

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param str request: request json
        :return:
        """
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)

            connectivity_flow = JuniperConnectivity(cli_configurator, logger)
            logger.info('Start applying connectivity changes, request is: {0}'.format(str(request)))
            result = connectivity_flow.apply_connectivity_changes(request=request)
            logger.info('Finished applying connectivity changes, response is: {0}'.format(str(result)))
            logger.info('Apply Connectivity changes completed')
            return result

    def save(self, context, folder_path, configuration_type, vrf_management_name):
        """Save selected file to the provided destination

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param configuration_type: source file, which will be saved
        :param folder_path: destination path where file will be saved
        :param vrf_management_name: VRF management Name
        :return str saved configuration file name:
        """
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)

            if not configuration_type:
                configuration_type = 'running'

            if not vrf_management_name:
                vrf_management_name = resource_config.vrf_management_name

            configuration_operations = JuniperConfigurationFlow(resource_config, logger, cli_configurator)
            logger.info('Save started')
            response = configuration_operations.save(folder_path=folder_path, configuration_type=configuration_type,
                                                     vrf_management_name=vrf_management_name)
            logger.info('Save completed')
            return response

    @GlobalLock.lock
    def restore(self, context, path, configuration_type, restore_method, vrf_management_name):
        """Restore selected file to the provided destination

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param path: source config file
        :param configuration_type: running or startup configs
        :param restore_method: append or override methods
        :param vrf_management_name: VRF management Name
        """
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)

            if not configuration_type:
                configuration_type = 'running'

            if not restore_method:
                restore_method = 'override'

            if not vrf_management_name:
                vrf_management_name = resource_config.vrf_management_name

            configuration_operations = JuniperConfigurationFlow(
                resource_config, logger, cli_configurator
            )
            logger.info('Restore started')
            configuration_operations.restore(path=path, restore_method=restore_method,
                                             configuration_type=configuration_type,
                                             vrf_management_name=vrf_management_name)
            logger.info('Restore completed')

    def orchestration_save(self, context, mode, custom_params):
        """

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param mode: mode
        :param custom_params: json with custom save parameters
        :return str response: response json
        """

        if not mode:
            mode = 'shallow'

        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)

            configuration_operations = JuniperConfigurationFlow(
                resource_config, logger, cli_configurator
            )

            logger.info('Orchestration save started')
            # response = configuration_operations.orchestration_save(mode=mode, custom_params=custom_params)
            response = configuration_operations.orchestration_save(mode=mode,
                                                                   custom_params=custom_params)
            response_json = OrchestrationSaveRestore(logger, resource_config.name).prepare_orchestration_save_result(
                response)
            logger.info('Orchestration save completed')
            return response_json

    def orchestration_restore(self, context, saved_artifact_info, custom_params):
        """

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param saved_artifact_info: OrchestrationSavedArtifactInfo json
        :param custom_params: json with custom restore parameters
        """
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)

            configuration_operations = JuniperConfigurationFlow(
                resource_config, logger, cli_configurator
            )

            logger.info('Orchestration restore started')
            configuration_operations.orchestration_restore(saved_artifact_info=saved_artifact_info,
                                                           custom_params=custom_params)
            logger.info('Orchestration restore completed')

            logger.info('Orchestration restore started')
            restore_params = OrchestrationSaveRestore(
                logger, resource_config.name
            ).parse_orchestration_save_result(saved_artifact_info, custom_params)
            configuration_operations.restore(**restore_params)
            logger.info('Orchestration restore completed')

    @GlobalLock.lock
    def load_firmware(self, context, path, vrf_management_name):
        """Upload and updates firmware on the resource

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :param path: full path to firmware file, i.e. tftp://10.10.10.1/firmware.tar
        :param vrf_management_name: VRF management Name
        """
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)

            if not vrf_management_name:
                vrf_management_name = resource_config.vrf_management_name

            logger.info('Start Load Firmware')
            firmware_operations = JuniperFirmwareFlow(logger, cli_configurator)
            response = firmware_operations.load_firmware(path=path, vrf_management_name=vrf_management_name)
            logger.info('Finish Load Firmware: {}'.format(response))

    def health_check(self, context):
        """Performs device health check

        :param ResourceCommandContext context: ResourceCommandContext object with all Resource Attributes inside
        :return: Success or Error message
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)

            state_operations = JuniperStateFlow(
                logger, resource_config, cli_configurator, api
            )
            return state_operations.health_check()

    def cleanup(self):
        pass

    def shutdown(self, context):
        with LoggingSessionContext(context) as logger:
            api = CloudShellSessionContext(context).get_api()

            resource_config = NetworkingResourceConfig.from_context(
                self.SHELL_NAME,
                context,
                api,
                self.SUPPORTED_OS,
            )
            cli_configurator = JuniperCliConfigurator(self._cli, resource_config, logger)

            state_operations = JuniperStateFlow(
                logger, resource_config, cli_configurator, api
            )
            return state_operations.shutdown()

