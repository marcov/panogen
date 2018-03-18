#
##
#
SRCS_DIR := src
OPENCV_VER := 320
BUILD_DIR := build
#CXXFLAGS=-Wl,--copy-dt-needed-entries -Wl,--no-as-needed

LDFLAGS := -lopencv_stitching -lopencv_imgcodecs -lopencv_imgproc -lopencv_core -lopencv_highgui -lopencv_features2d

EXECUTABLES := MatchTemplate_Demo-$(OPENCV_VER) stitching-$(OPENCV_VER) compareHist_Demo #kaze

EXECUTABLES := $(foreach exec,$(EXECUTABLES), $(addprefix $(BUILD_DIR)/, $(exec)))


.PHONY: all
all: $(EXECUTABLES)

$(BUILD_DIR):
	mkdir -p $@
	ln -s ./compareHist_Demo  $(BUILD_DIR)/comparator
	ln -s ./stitching-$(OPENCV_VER) $(BUILD_DIR)/stitcher

$(BUILD_DIR)/% : $(SRCS_DIR)/%.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -rf $(BUILD_DIR)
