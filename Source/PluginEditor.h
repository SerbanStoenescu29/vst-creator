#pragma once

#include <JuceHeader.h>
#include "PluginProcessor.h"

class VstAiDemoAudioProcessorEditor final : public juce::AudioProcessorEditor
{
public:
    explicit VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor&);
    ~VstAiDemoAudioProcessorEditor() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    VstAiDemoAudioProcessor& processor;
    
    // Header components
    juce::Label titleLabel;
    
    // Delay Time knob
    juce::Slider delayTimeSlider;
    juce::Label delayTimeLabel;
    juce::Label delayTimeValueLabel;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> delayTimeAttachment;
    
    // Mix knob
    juce::Slider mixSlider;
    juce::Label mixLabel;
    juce::Label dryLabel;
    juce::Label wetLabel;
    juce::Label mixValueLabel;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mixAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(VstAiDemoAudioProcessorEditor)
};
