import asyncio
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import asyncua
from asyncua import Server, ua

_logger = logging.getLogger(__name__)


async def load_nodesets(server: Server) -> tuple:
    nodeset_dir = Path(__file__).parent.joinpath("nodesets")

    _logger.info("Importing OPC UA DI nodeset...")
    await server.import_xml(nodeset_dir.joinpath("Opc.Ua.Di.v1.05.03.NodeSet2.xml"))
    opc_ua_di_ns = await server.get_namespace_index("http://opcfoundation.org/UA/DI/")

    _logger.info("Patching example nodeset...")
    # We need to patch the `Version` and `PublicationDate` of the required UA nodeset in the exported nodeset of our
    # model because asyncua does not yet ship with the most recent v1.05.03 version and therefore we wouldn't be
    # able to import our model. UaModeler does not allow to change the base UA nodeset and thus always exports our
    # model with the required version set to v1.05.02 and the publication date set to 2022-11-01.
    nodeset2_path = nodeset_dir.joinpath("asyncua-references-instantiate-issue.xml")
    nodeset2_xml_root = ET.parse(nodeset2_path).getroot()
    # http://xpather.com/bzitxYfG
    required_model_node = nodeset2_xml_root.find(
        './/{*}RequiredModel[@ModelUri="http://opcfoundation.org/UA/"]'
    )
    required_model_node.set("Version", "1.05.01")
    required_model_node.set("PublicationDate", "2022-01-01T00:00:00Z")

    _logger.info("Importing example nodeset...")
    await server.import_xml(xmlstring=ET.tostring(nodeset2_xml_root))
    example_ns = await server.get_namespace_index("http://example.com/UA/")

    return opc_ua_di_ns, example_ns


async def instantiate_my_device(
    device_name: str, server: Server, opc_ua_di_ns: int, example_ns: int
) -> asyncua.common.Node:
    type_node = await server.nodes.base_object_type.get_child(
        (
            f"{opc_ua_di_ns}:TopologyElementType",
            f"{opc_ua_di_ns}:ComponentType",
            f"{opc_ua_di_ns}:DeviceType",
            f"{example_ns}:MyDeviceType",
        )
    )

    _logger.info(f"Instantiating new device node for {device_name}...")

    device_set_node = await server.nodes.objects.get_child(f"{opc_ua_di_ns}:DeviceSet")

    return await device_set_node.add_object(
        ua.NodeId(5501, example_ns),
        ua.QualifiedName(device_name, example_ns),
        type_node,
        instantiate_optional=False,
    )


async def main() -> None:

    server = Server()
    await server.init()
    # Windows doesn't allow to use port 4840
    server.set_endpoint("opc.tcp://0.0.0.0:44840/example/server/")

    opc_ua_di_ns, example_ns = await load_nodesets(server)

    await instantiate_my_device("MyDevice2", server, opc_ua_di_ns, example_ns)

    _logger.info("Starting server!")
    async with server:
        _logger.info("Server started!")
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    _LOGGING_FORMAT = (
        "%(asctime)s [%(threadName)-{thread_name_len}.{thread_name_len}s] %(levelname)-8s| "
        "%(name)s %(module)s.%(funcName)s (%(lineno)s): %(message)s"
    )
    logging.basicConfig(
        level=logging.DEBUG, format=_LOGGING_FORMAT.format(thread_name_len=12)
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
