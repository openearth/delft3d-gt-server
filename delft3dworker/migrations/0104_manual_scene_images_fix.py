def forwards_func(apps, schema_editor):
    Scene = apps.get_model("delft3dworker", "Scene")
    db_alias = schema_editor.connection.alias

    for scene in Scene.objects.using(db_alias).all():
        for key, value in scene.info.items():
            if key == "delta_fringe_images":
                value["name"] = "Delta Fringe"
                value[
                    "text"
                ] = """This graph shows the position of the delta plain fringe superimposed on the graph of the water depth. This is an indicator for the large-scale plan-view morphology of a delta, which is a function of the dominant forcing processes (waves, rivers, tides) and grain size of transported sediments."""
                value["pattern"] = "delta_fringe"
            if key == "subenvironment_images":
                value["name"] = "Subenvironment"
                value["text"] = ""
                value["pattern"] = "subenvironment"
            if key == "channel_network_images":
                value["name"] = "Channel Network"
                value[
                    "text"
                ] = """These graphs display the properties, the architecture and the  evolution of the channel network. Fluvial deposits are targets for hydrocarbon and groundwater exploration as they are typically permeable and continuous, and consequently a potential reservoir or aquifer."""
                value["pattern"] = "channel_network"
            if key == "sediment_fraction_images":
                value["name"] = "Sediment Fraction"
                value[
                    "text"
                ] = """In this cross-shore section the sand fraction of the accumulated sediments and the stratigraphic build-up of the delta are displayed. These are direct outputs from Delft3D. Thanks to these image it is possible to describe the grain size trends (proximal to distal in this case) and the geometry of sediment bodies within the delta, such as shoreface sand wedges and clay drapes. These are are important factors controlling the size and the heterogeneity of a reservoir."""
                value["pattern"] = "sediment_fraction"


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("delft3dworker", "0103_alter_template_yaml_template.py"),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
