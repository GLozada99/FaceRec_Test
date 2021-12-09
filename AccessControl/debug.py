import AccessControl.Data.crud as crud
import AccessControl.Data.classes as classes


camera_1 = crud.get_entry(classes.Camera, 1)

print(camera_1.connection_string())
