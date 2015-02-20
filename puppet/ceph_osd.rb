Facter.add("osd_devices_list") do
    setcode do
        devs = %x{lsblk -ln | awk '{if ($6 == "disk") print $1}'}.split("\n")
        prepare = []
        activate = []
        osds = []
        journals = []
        output = ""

        # Finds OSD and journal devices based on Partition GUID
        devs.each { |d|
            # lsblk returns cciss devices as cciss!c0d0p1. The entries
            # in /dev are cciss/c0d0p1
            if d.gsub!(/!/, '/')
              sep = 'p'
            else
              sep = ''
            end
            device = "/dev/#{d}#{sep}"
            parts = %x{ls /dev/#{d}?*}.gsub(device,"").split("\n")
            parts.each { |p|
                code = %x{sgdisk -i #{p} /dev/#{d} | grep "Partition GUID code" | awk '{print $4}'}.strip()
                case code
                when "4FBD7E29-9D25-41B8-AFD0-062C0CEFF05D"
                    # Only use unmounted devices
                    if %x{grep -c #{device}#{p} /proc/mounts}.to_i == 0
                        mp = %x{mktemp -d}.strip()
                        begin
                            mp_code = %x{mount #{device}#{p} #{mp} && test -f #{mp}/fsid && echo 0 || echo 1}.to_i
                        rescue
                        else
                            osds << ["#{device}#{p}", !mp_code.zero?]
                        ensure
                            %x{umount -f #{mp}}
                        end
                    end
                when "45B0969E-9B03-4F30-B4C6-B4B80CEFF106"
                    if %x{grep -c #{device}#{p} /proc/mounts}.to_i == 0
                        journals << "#{device}#{p}"
                    end
                end
            }
        }

        osds.each { |osd, prep|
          journal = journals.shift
          if journal
            osd_disk = "#{osd}:#{journal}"
          else
            osd_disk = osd
          end 
          if prep == true
              prepare << osd_disk
          end
          activate << osd_disk
        }
        if !(prepare.empty? and activate.empty?)
            output = [prepare.join(" "), activate.join(" ")].join(";")
        end
        output
    end
end
