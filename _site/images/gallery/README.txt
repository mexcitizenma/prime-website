Gallery photos. gallery.html and es/gallery.html reference these filenames
directly; any file that is missing shows a neutral "Photo coming soon" tile
instead of a broken image, so a tile can wait for its photo.

REAL Prime Paint job photos now in place (cropped 4:3, ~1100px, under 250 KB):

  interior-ceiling-cut-in.jpg     interior-bedroom-grey.jpg
  interior-windows-trim.jpg       interior-stairs-risers.jpg
  interior-corridor-two-tone.jpg  interior-hallway-yellow.jpg
  interior-commercial-dining.jpg  cabinets-kitchen-white.jpg
  cabinets-kitchen-hood.jpg       cabinets-vanity.jpg
  cabinets-doors-drying.jpg       exterior-porch.jpg
  flooring-laminate.jpg           flooring-hardwood.jpg

Still placeholders — no real photo exists for these yet:

  exterior-siding.jpg             exterior-deck-stain.jpg
  epoxy-garage-flake.jpg          epoxy-basement.jpg
  pressure-wash-driveway.jpg      siding-clean-before-after.jpg
  fence-stain.jpg                 tv-mount.jpg

Originals live in images/stock/<category>/. To add one, crop to 4:3 and resize:

  cp "images/stock/<cat>/IMG_XXXX.JPG" /tmp/w.jpg
  sips -c 1152 1536 --cropOffset <y> 0 /tmp/w.jpg          # 4:3 window, y picks the framing
  sips -Z 1100 -s format jpeg -s formatOptions 62 /tmp/w.jpg --out images/gallery/<name>.jpg

Then update the alt text and caption in gallery.html and es/gallery.html to
match what is actually in the photo. Keep each file under ~250 KB.
